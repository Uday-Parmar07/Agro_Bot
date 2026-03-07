"""Government schemes helper using Tavily search + Groq Llama.

This module searches official government sites for farmer schemes and asks
Groq's Llama model to summarize suitable programs based on questionnaire data.
"""

import json
import os
import re
from typing import Dict, Any, List, Tuple

from dotenv import load_dotenv
from tavily import TavilyClient
from groq import Groq


load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TAVILY_API_KEY:
    raise RuntimeError("TAVILY_API_KEY not set. Add it to your environment or .env file.")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY not set. Add it to your environment or .env file.")


ALLOWED_DOMAINS: List[str] = [
    "gov.in",
    "nic.in",
    "agricoop.nic.in",
    "mp.gov.in",
    "maharashtra.gov.in",
    "up.gov.in",
    "punjab.gov.in",
]

tavily = TavilyClient(api_key=TAVILY_API_KEY)
groq_client = Groq(api_key=GROQ_API_KEY)


def _domain_from_url(url: str) -> str:
    if not url:
        return ""
    match = re.search(r"https?://([^/]+)", url)
    return match.group(1) if match else ""


def _search_government_schemes(location: str, crop_focus: str = "") -> Tuple[str, List[Dict[str, str]]]:
    """Search official government domains with deeper, multi-query retrieval."""
    queries = [
        f"farmer scheme {location} eligibility how to apply official site",
        f"agriculture subsidy {location} farmer apply portal gov.in",
    ]
    if crop_focus:
        queries.append(f"{crop_focus} farmer scheme {location} eligibility official")

    all_results: List[Dict[str, Any]] = []
    for query in queries:
        try:
            result = tavily.search(
                query=query,
                include_domains=ALLOWED_DOMAINS,
                max_results=8,
                search_depth="advanced",
            )
        except Exception:
            result = tavily.search(
                query=query,
                include_domains=ALLOWED_DOMAINS,
                max_results=6,
                search_depth="basic",
            )
        all_results.extend(result.get("results", []))

    seen_urls = set()
    sources: List[Dict[str, str]] = []
    combined_chunks: List[str] = []

    for item in all_results:
        url = (item.get("url") or "").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        title = (item.get("title") or url).strip()
        content = (item.get("content") or "").strip()
        domain = (item.get("source") or _domain_from_url(url)).strip()

        source = {
            "title": title,
            "url": url,
            "domain": domain,
            "content": content,
        }
        sources.append(source)

        if content:
            combined_chunks.append(f"[{title}] {content}")

    return "\n\n".join(combined_chunks), sources[:10]


def _build_prompt(user_data: Dict[str, Any], schemes_text: str) -> str:
    location = user_data.get("location") or user_data.get("state") or "Unknown"
    acreage = user_data.get("acreage") or user_data.get("farm_size")
    crops = user_data.get("crops") or user_data.get("preferred_crops") or []
    irrigation = user_data.get("irrigation") or user_data.get("water_source")
    soil = user_data.get("soil_type")

    crop_line = ", ".join(crops) if isinstance(crops, list) else crops or "N/A"
    acreage_line = f"Farm size: {acreage}" if acreage else ""
    irrigation_line = f"Irrigation: {irrigation}" if irrigation else ""
    soil_line = f"Soil: {soil}" if soil else ""

    profile = " | ".join(p for p in [acreage_line, irrigation_line, soil_line] if p)

    return f"""
You are an assistant that recommends official Indian government farmer schemes.
Use only the supplied government data.

Farmer location: {location}
Primary crops: {crop_line}
Profile: {profile if profile else 'N/A'}

Government data (unstructured):
{schemes_text}

Return ONLY valid JSON with this exact schema:
{{
    "summary": "short summary in 2-3 lines",
    "schemes": [
        {{
            "name": "scheme name",
            "brief_description": "specific description based on source snippet",
            "eligibility": "specific eligibility from source; if unavailable, infer cautiously from source context",
            "how_to_apply": "specific portal/office/application route from source"
        }}
    ]
}}

Rules:
- Include 3 to 5 schemes.
- Do not use markdown.
- Do not include any text outside JSON.
- Avoid vague placeholders like "check official notification".
"""


def _is_vague_text(value: str) -> bool:
    text = (value or "").strip().lower()
    if not text:
        return True
    vague_markers = [
        "not specified in source data",
        "check official notification",
        "official government source",
        "relevant scheme information",
    ]
    return any(marker in text for marker in vague_markers)


def _clean_snippet(text: str, max_len: int = 220) -> str:
    clean = re.sub(r"\s+", " ", (text or "")).strip()
    if not clean:
        return ""
    if len(clean) <= max_len:
        return clean
    return clean[: max_len - 1].rstrip() + "…"


def _first_sentence_matching(content: str, patterns: List[str]) -> str:
    if not content:
        return ""
    text = re.sub(r"\s+", " ", content)
    sentences = re.split(r"(?<=[\.!?])\s+", text)
    for sentence in sentences:
        lower = sentence.lower()
        if any(re.search(pattern, lower) for pattern in patterns):
            return _clean_snippet(sentence)
    return ""


def _extract_details_from_content(content: str, url: str) -> Dict[str, str]:
    brief = _first_sentence_matching(
        content,
        [
            r"\bscheme\b",
            r"\bsubsid",
            r"\bfinancial assistance\b",
            r"\bbenefit",
        ],
    ) or _clean_snippet(content)

    eligibility = _first_sentence_matching(
        content,
        [
            r"\beligib",
            r"\bbeneficiar",
            r"\bfarmer(s)?\s+(who|with)",
            r"\blandholding\b",
            r"\bsmall\s+and\s+marginal\b",
        ],
    )

    how_to_apply = _first_sentence_matching(
        content,
        [
            r"\bapply\b",
            r"\bapplication\b",
            r"\bregister\b",
            r"\bportal\b",
            r"\bonline\b",
            r"\bvisit\b",
        ],
    )

    if not eligibility:
        eligibility = "Refer source for exact eligibility criteria and required landholding/income conditions."
    if not how_to_apply:
        how_to_apply = f"Apply through the official portal/office: {url}" if url else "Apply via the official agriculture department portal."

    return {
        "brief_description": brief or "Details available in official source link.",
        "eligibility": eligibility,
        "how_to_apply": how_to_apply,
    }


def _find_best_source_for_scheme(name: str, sources: List[Dict[str, str]]) -> Dict[str, str]:
    if not name:
        return {}

    name_tokens = set(re.findall(r"[a-z0-9]+", name.lower()))
    best_source: Dict[str, str] = {}
    best_score = 0

    for source in sources:
        title = (source.get("title") or "").lower()
        title_tokens = set(re.findall(r"[a-z0-9]+", title))
        score = len(name_tokens & title_tokens)
        if score > best_score:
            best_score = score
            best_source = source

    if best_source:
        return best_source
    return sources[0] if sources else {}


def _normalize_schemes(items: List[Dict[str, Any]], sources: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Normalize scheme objects to consistent shape and enrich vague fields from source snippets."""
    normalized: List[Dict[str, str]] = []
    for item in items:
        name = str(item.get("name", "")).strip()
        if not name:
            continue

        source = _find_best_source_for_scheme(name, sources)
        source_content = source.get("content", "") if source else ""
        source_url = source.get("url", "") if source else ""
        extracted = _extract_details_from_content(source_content, source_url)

        brief = str(item.get("brief_description", "")).strip()
        eligibility = str(item.get("eligibility", "")).strip()
        how_to_apply = str(item.get("how_to_apply", "")).strip()

        if _is_vague_text(brief):
            brief = extracted["brief_description"]
        if _is_vague_text(eligibility):
            eligibility = extracted["eligibility"]
        if _is_vague_text(how_to_apply):
            how_to_apply = extracted["how_to_apply"]

        normalized.append(
            {
                "name": name,
                "brief_description": brief or extracted["brief_description"],
                "eligibility": eligibility or extracted["eligibility"],
                "how_to_apply": how_to_apply or extracted["how_to_apply"],
            }
        )

    return normalized[:5]


def _extract_schemes_from_text(text: str) -> List[Dict[str, str]]:
    """Fallback extraction for non-JSON responses."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    result: List[Dict[str, str]] = []
    for line in lines:
        clean = re.sub(r"^\d+\.\s*", "", line)
        clean = re.sub(r"^[-•]\s*", "", clean)
        if not clean:
            continue
        if any(prefix in clean.lower() for prefix in ["brief description:", "eligibility:", "how to apply:"]):
            continue
        result.append(
            {
                "name": clean[:120],
                "brief_description": "",
                "eligibility": "",
                "how_to_apply": "",
            }
        )
        if len(result) >= 5:
            break
    return result


def _clean_summary(text: str) -> str:
    """Remove markdown bold/numbering for cleaner UI display."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"^\s*\d+\.\s*", "• ", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-–]\s*", "• ", text, flags=re.MULTILINE)
    return text.strip()


def _parse_llm_response(raw_text: str, sources: List[Dict[str, str]]) -> Dict[str, Any]:
    """Parse model output as JSON, with safe fallback extraction."""
    cleaned = raw_text.strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                parsed = json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                parsed = {
                    "summary": _clean_summary(cleaned),
                    "schemes": _extract_schemes_from_text(cleaned),
                }
        else:
            parsed = {
                "summary": _clean_summary(cleaned),
                "schemes": _extract_schemes_from_text(cleaned),
            }

    summary = _clean_summary(parsed.get("summary", ""))
    schemes = _normalize_schemes(parsed.get("schemes", []), sources)
    return {
        "summary": summary,
        "schemes": schemes,
    }


def _fallback_from_sources(location: str, sources: List[Dict[str, str]]) -> Dict[str, Any]:
    """Fallback response when LLM enrichment is unavailable."""
    schemes: List[Dict[str, str]] = []
    for source in sources[:5]:
        title = (source.get("title") or "Government Scheme").strip()
        url = (source.get("url") or "").strip()
        content = (source.get("content") or "").strip()
        extracted = _extract_details_from_content(content, url)

        schemes.append(
            {
                "name": title,
                "brief_description": extracted["brief_description"],
                "eligibility": extracted["eligibility"],
                "how_to_apply": extracted["how_to_apply"],
            }
        )

    if not schemes:
        schemes = [
            {
                "name": "No schemes extracted",
                "brief_description": "Could not extract schemes from official sources at this time.",
                "eligibility": "Data unavailable in fetched source snippets.",
                "how_to_apply": "Try again later or check state agriculture department portals.",
            }
        ]

    return {
        "summary": (
            f"Showing official-source scheme links for {location}. AI enrichment is temporarily unavailable; "
            "details below are extracted from government-source snippets and links."
        ),
        "schemes": schemes,
        "sources": sources,
        "llm_enhanced": False,
    }


def generate_government_schemes(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch schemes and summarize via Groq Llama based on questionnaire data."""
    location = user_data.get("location") or user_data.get("state") or "India"
    crop_focus = ""
    crops = user_data.get("crops") or user_data.get("preferred_crops")
    if isinstance(crops, list) and crops:
        crop_focus = crops[0]
    elif isinstance(crops, str):
        crop_focus = crops

    schemes_text, sources = _search_government_schemes(location, crop_focus)
    prompt = _build_prompt(user_data, schemes_text)

    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1000,
        )

        raw_response = completion.choices[0].message.content
        parsed = _parse_llm_response(raw_response, sources)

        return {
            "summary": parsed["summary"],
            "schemes": parsed["schemes"],
            "sources": sources,
            "llm_enhanced": True,
        }
    except Exception:
        return _fallback_from_sources(location=location, sources=sources)


if __name__ == "__main__":
    demo_user = {
        "location": "Madhya Pradesh",
        "crops": ["wheat", "soybean"],
        "acreage": "3 acres",
        "irrigation": "canal",
        "soil_type": "black soil",
    }
    print(generate_government_schemes(demo_user))
