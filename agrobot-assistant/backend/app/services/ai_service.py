import io
import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq
from pydantic import ValidationError

from app.models.farm_context import DataQualityAssessment, DataQualityLevel, FarmContext
from app.models.recommendation import (
    CandidateSource,
    CropCandidate,
    CropExplanation,
    ExplanationFailureCode,
    LLMExplanationResponse,
)
from app.services.crop_catalog_service import canonical_crop_slug, crop_catalog_service
from app.utils.prompt_generator import generate_crop_explanation_prompt


logger = logging.getLogger(__name__)
APP_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = APP_DIR.parent


@dataclass
class ExplanationGenerationResult:
    response: LLMExplanationResponse
    used_llm: bool
    reason_codes: list[ExplanationFailureCode] = field(default_factory=list)

    @property
    def public_status(self) -> str:
        if not self.used_llm:
            return "template_fallback"
        return "partial_template" if self.reason_codes else "generated"


class ExplanationValidationError(ValueError):
    def __init__(self, code: ExplanationFailureCode):
        self.code = code
        super().__init__(code.value)


class AIService:
    def __init__(self):
        # Load both supported local locations explicitly so the service does not
        # depend on the process working directory. Values are never logged.
        load_dotenv(BACKEND_DIR / ".env")
        load_dotenv(APP_DIR / ".env")
        self.enabled = os.getenv("ENABLE_LLM_EXPLANATIONS", "true").lower() in {
            "1",
            "true",
            "yes",
        }
        api_key = os.getenv("GROQ_API_KEY")
        timeout_seconds = float(os.getenv("GROQ_TIMEOUT_SECONDS", "20"))
        self.client = Groq(api_key=api_key, timeout=timeout_seconds) if api_key and self.enabled else None
        self._missing_api_key = not bool(api_key)
        if not self.enabled:
            self._log_reason(ExplanationFailureCode.LLM_DISABLED)
        elif self._missing_api_key:
            self._log_reason(ExplanationFailureCode.LLM_API_KEY_MISSING)

    async def generate_crop_explanations(
        self,
        candidates: list[CropCandidate],
        context: FarmContext,
        data_quality: DataQualityAssessment,
        preferred_language: str = "en",
    ) -> ExplanationGenerationResult:
        templates = self._template_response(candidates, data_quality, preferred_language)
        if not candidates:
            return ExplanationGenerationResult(
                response=templates,
                used_llm=False,
                reason_codes=[ExplanationFailureCode.LLM_DISABLED],
            )
        if not self.enabled:
            return self._fallback(templates, ExplanationFailureCode.LLM_DISABLED)
        if self.client is None:
            return self._fallback(templates, ExplanationFailureCode.LLM_API_KEY_MISSING)

        profiles = {
            candidate.crop_slug: crop_catalog_service.get_crop_profile(candidate.crop_slug)
            for candidate in candidates
        }
        if any(profile is None for profile in profiles.values()):
            return self._fallback(templates, ExplanationFailureCode.LLM_INTERNAL_ERROR)

        prompt = generate_crop_explanation_prompt(
            candidates, profiles, context, data_quality, preferred_language
        )
        allow_list = [candidate.crop_slug for candidate in candidates]
        try:
            completion = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You explain an already ranked crop list. Return only valid JSON matching this schema: "
                            '{"crop_explanations":[{"crop_slug":"allowed-slug","summary":"text",'
                            '"why_recommended":["text"],"main_risks":["text"],"next_actions":["text"],'
                            '"soil_advice":["text"],"irrigation_advice":["text"],"pest_prevention":["text"]}],'
                            '"general_advice":["text"],"disclaimer":"text"}. '
                            "Crop order in your JSON is irrelevant because the server restores authoritative ranking. "
                            "Do not add or rename crops, invent varieties, yield, prices, costs, profitability, "
                            "probabilities, citations, numerical claims, government affiliation, or facts absent "
                            "from verified_profile_facts. Do not infer missing catalogue facts."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=1800,
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            code = self._request_failure_code(exc)
            self._log_reason(code, exc)
            return ExplanationGenerationResult(templates, False, [code])

        try:
            parsed = json.loads(self._clean_json(completion.choices[0].message.content))
        except (json.JSONDecodeError, TypeError, AttributeError, IndexError, KeyError) as exc:
            self._log_reason(ExplanationFailureCode.LLM_INVALID_JSON, exc)
            return ExplanationGenerationResult(
                templates, False, [ExplanationFailureCode.LLM_INVALID_JSON]
            )

        try:
            response = LLMExplanationResponse(**parsed)
        except ValidationError as exc:
            self._log_reason(ExplanationFailureCode.LLM_SCHEMA_VALIDATION_FAILED, exc)
            return ExplanationGenerationResult(
                templates,
                False,
                [ExplanationFailureCode.LLM_SCHEMA_VALIDATION_FAILED],
            )

        try:
            normalized, reason_codes = self._normalize_response(response, templates, allow_list)
        except ExplanationValidationError as exc:
            self._log_reason(exc.code, exc)
            return ExplanationGenerationResult(templates, False, [exc.code])
        except Exception as exc:
            self._log_reason(ExplanationFailureCode.LLM_INTERNAL_ERROR, exc)
            return ExplanationGenerationResult(
                templates, False, [ExplanationFailureCode.LLM_INTERNAL_ERROR]
            )
        for code in reason_codes:
            self._log_reason(code)
        return ExplanationGenerationResult(normalized, True, reason_codes)

    def _normalize_response(
        self,
        response: LLMExplanationResponse,
        templates: LLMExplanationResponse,
        allow_list: list[str],
    ) -> tuple[LLMExplanationResponse, list[ExplanationFailureCode]]:
        normalized_items = []
        for item in response.crop_explanations:
            slug = canonical_crop_slug(item.crop_slug)
            normalized_items.append(item.model_copy(update={"crop_slug": slug}))
        returned_slugs = [item.crop_slug for item in normalized_items]
        if len(returned_slugs) != len(set(returned_slugs)):
            raise ExplanationValidationError(ExplanationFailureCode.LLM_DUPLICATE_CROP)
        if set(returned_slugs) - set(allow_list):
            raise ExplanationValidationError(ExplanationFailureCode.LLM_UNAUTHORIZED_CROP)

        response = response.model_copy(update={"crop_explanations": normalized_items})
        cleaned, removed_unsafe_claim = self._remove_unsupported_claims(response, templates)
        returned = {item.crop_slug: item for item in cleaned.crop_explanations}
        fallback = {item.crop_slug: item for item in templates.crop_explanations}
        missing = [slug for slug in allow_list if slug not in returned]
        ordered = [returned.get(slug, fallback[slug]) for slug in allow_list]
        reason_codes = []
        if missing:
            reason_codes.append(ExplanationFailureCode.LLM_MISSING_CROP)
        if removed_unsafe_claim:
            reason_codes.append(ExplanationFailureCode.LLM_UNSUPPORTED_NUMERIC_CLAIM)
        return cleaned.model_copy(update={"crop_explanations": ordered}), reason_codes

    def _remove_unsupported_claims(
        self,
        response: LLMExplanationResponse,
        templates: LLMExplanationResponse,
    ) -> tuple[LLMExplanationResponse, bool]:
        template_by_slug = {item.crop_slug: item for item in templates.crop_explanations}
        cleaned = []
        removed = False
        for item in response.crop_explanations:
            fallback = template_by_slug[item.crop_slug]
            values = item.model_dump()
            if self._unsupported_claim(item.summary):
                values["summary"] = fallback.summary
                removed = True
            for field_name in (
                "why_recommended",
                "main_risks",
                "next_actions",
                "soil_advice",
                "irrigation_advice",
                "pest_prevention",
            ):
                original = getattr(item, field_name)
                safe_items = [text for text in original if not self._unsupported_claim(text)]
                if len(safe_items) != len(original):
                    removed = True
                values[field_name] = safe_items or getattr(fallback, field_name)
            cleaned.append(CropExplanation(**values))
        general = [text for text in response.general_advice if not self._unsupported_claim(text)]
        if len(general) != len(response.general_advice):
            removed = True
        return (
            LLMExplanationResponse(
                crop_explanations=cleaned,
                general_advice=general or templates.general_advice,
                disclaimer=templates.disclaimer,
            ),
            removed,
        )

    @staticmethod
    def _unsupported_claim(text: str) -> bool:
        value = str(text or "")
        return bool(
            re.search(r"\d|[%₹$€£]", value)
            or re.search(r"\b(price|profit|yield|variety|quintal|ton(?:ne)?|kg|rupee)\b", value, re.I)
        )

    def _template_response(
        self,
        candidates: list[CropCandidate],
        data_quality: DataQualityAssessment,
        language: str,
    ) -> LLMExplanationResponse:
        hindi = language == "hi"
        explanations = []
        for candidate in candidates:
            model_backed = CandidateSource.XGBOOST in candidate.candidate_sources
            knowledge_backed = CandidateSource.KNOWLEDGE_BASE in candidate.candidate_sources
            coverage = getattr(candidate, "validation_coverage_summary", None)
            no_verified_checks = bool(coverage and coverage.verified_checks == 0)
            if hindi:
                if no_verified_checks:
                    summary = "यह केवल प्रारंभिक ML पैटर्न है; फसल की स्थानीय कृषि उपयुक्तता सत्यापित नहीं हो सकी।"
                elif model_backed and knowledge_backed:
                    summary = "यह फसल ML मॉडल और सत्यापित फसल ज्ञान, दोनों से समर्थित उम्मीदवार है।"
                elif model_backed:
                    summary = "यह फसल AgroBot के ML-समर्थित फसल वर्गों में मजबूत मिलान थी।"
                else:
                    summary = "यह फसल सत्यापित फसल ज्ञान से मिली है और वर्तमान ML मॉडल में शामिल नहीं है।"
                action = "स्थानीय कृषि विशेषज्ञ से परिस्थितियों की पुष्टि करें और मिट्टी की जाँच कराएँ।"
            else:
                if no_verified_checks:
                    summary = (
                        "This is only a preliminary ML pattern; crop-specific local agronomic "
                        "suitability could not be verified."
                    )
                elif model_backed and knowledge_backed:
                    summary = "This candidate is supported by both the ML model and verified crop knowledge."
                elif model_backed:
                    summary = "This crop was among the strongest matches across AgroBot's ML-supported crop classes."
                else:
                    summary = "This crop came from AgroBot's verified crop knowledge base and is not covered by the current ML model."
                action = "Confirm local conditions with an agricultural adviser and obtain a soil test before planting."
            reasons = candidate.matched_conditions or [summary]
            risks = [warning.message for warning in candidate.warnings]
            explanations.append(
                CropExplanation(
                    crop_slug=candidate.crop_slug,
                    summary=summary,
                    why_recommended=reasons,
                    main_risks=risks,
                    next_actions=[action],
                    soil_advice=[],
                    irrigation_advice=[],
                    pest_prevention=[],
                )
            )
        reliability_advice = (
            "मिट्टी और जलवायु के विश्वसनीय आँकड़े उपलब्ध होने पर सुझाव दोबारा बनाएँ।"
            if hindi
            else "Update missing farm information before generating a new recommendation."
        )
        disclaimer = (
            "यह प्रारंभिक निर्णय-सहायता है, रोपण या वित्तीय परिणाम की गारंटी नहीं।"
            if hindi
            else "This is decision support, not a guarantee of planting or financial outcomes."
        )
        general = [reliability_advice] if data_quality.level == DataQualityLevel.LOW else []
        return LLMExplanationResponse(
            crop_explanations=explanations,
            general_advice=general,
            disclaimer=disclaimer,
        )

    @staticmethod
    def _request_failure_code(exc: Exception) -> ExplanationFailureCode:
        name = exc.__class__.__name__.lower()
        status_code = getattr(exc, "status_code", None)
        if "timeout" in name:
            return ExplanationFailureCode.LLM_TIMEOUT
        if "ratelimit" in name or status_code == 429:
            return ExplanationFailureCode.LLM_RATE_LIMITED
        if "api" in name or "connection" in name or "request" in name:
            return ExplanationFailureCode.LLM_REQUEST_FAILED
        return ExplanationFailureCode.LLM_INTERNAL_ERROR

    @staticmethod
    def _log_reason(code: ExplanationFailureCode, exc: Exception | None = None) -> None:
        exception_type = exc.__class__.__name__ if exc else "none"
        logger.warning(
            "Crop explanation fallback reason_code=%s exception_type=%s",
            code.value,
            exception_type,
        )

    def _fallback(
        self,
        templates: LLMExplanationResponse,
        code: ExplanationFailureCode,
    ) -> ExplanationGenerationResult:
        self._log_reason(code)
        return ExplanationGenerationResult(templates, False, [code])

    @staticmethod
    def _clean_json(value: str) -> str:
        text = re.sub(r"```(?:json)?\s*", "", value or "").replace("```", "").strip()
        start, end = text.find("{"), text.rfind("}")
        return text[start : end + 1] if start >= 0 and end >= start else text

    async def transcribe_audio(self, filename: str, content: bytes, content_type: str) -> str:
        if self.client is None:
            return ""
        try:
            audio_file = io.BytesIO(content)
            audio_file.name = filename or "audio.webm"
            transcript = self.client.audio.transcriptions.create(
                file=(audio_file.name, audio_file, content_type),
                model="whisper-large-v3",
            )
            return getattr(transcript, "text", "") or ""
        except Exception as exc:
            logger.warning("Voice transcription failed exception_type=%s", exc.__class__.__name__)
            return ""


ai_service = AIService()
