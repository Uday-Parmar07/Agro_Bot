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


def _search_government_schemes(location: str, crop_focus: str = "") -> Tuple[str, List[Dict[str, str]]]:
	"""Search official government domains for farmer schemes text."""
	query_parts = ["farmer schemes", location]
	if crop_focus:
		query_parts.append(crop_focus)
	query = " ".join(q for q in query_parts if q)

	results = tavily.search(
		query=query,
		include_domains=ALLOWED_DOMAINS,
		max_results=6,
		search_depth="basic",
	)
	sources = [
		{
			"title": r.get("title") or r.get("url", ""),
			"url": r.get("url", ""),
			"domain": r.get("source", ""),
		}
		for r in results.get("results", [])
	]

	return "\n\n".join(r.get("content", "") for r in results.get("results", [])), sources


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
			"brief_description": "short description",
			"eligibility": "eligibility details",
			"how_to_apply": "application steps or portal"
		}}
	]
}}

Rules:
- Include 3 to 5 schemes.
- Do not use markdown.
- Do not include any text outside JSON.
- If some field is unknown from provided data, set it to "Not specified in source data".
"""


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
			model="llama-3.1-8b-instant",
			messages=[{"role": "user", "content": prompt}],
			temperature=0.2,
			max_tokens=900,
		)

		raw_response = completion.choices[0].message.content
		parsed = _parse_llm_response(raw_response)
		summary = _clean_summary(parsed.get("summary", ""))
		schemes = _normalize_schemes(parsed.get("schemes", []))

		return {
			"summary": summary,
			"schemes": schemes,
			"sources": sources,
			"llm_enhanced": True,
		}
	except Exception:
		return _fallback_from_sources(location=location, sources=sources)


def _parse_llm_response(raw_text: str) -> Dict[str, Any]:
	"""Parse model output as JSON, with safe fallback extraction."""
	cleaned = raw_text.strip()
	try:
		return json.loads(cleaned)
	except json.JSONDecodeError:
		start = cleaned.find("{")
		end = cleaned.rfind("}")
		if start != -1 and end != -1 and end > start:
			try:
				return json.loads(cleaned[start : end + 1])
			except json.JSONDecodeError:
				pass

		fallback_summary = _clean_summary(cleaned)
		fallback_schemes = _extract_schemes_from_text(cleaned)
		return {
			"summary": fallback_summary,
			"schemes": fallback_schemes,
		}


def _normalize_schemes(items: List[Dict[str, Any]]) -> List[Dict[str, str]]:
	"""Normalize scheme objects to consistent shape."""
	normalized: List[Dict[str, str]] = []
	for item in items:
		name = str(item.get("name", "")).strip()
		if not name:
			continue
		normalized.append(
			{
				"name": name,
				"brief_description": str(item.get("brief_description", "Not specified in source data")).strip() or "Not specified in source data",
				"eligibility": str(item.get("eligibility", "Not specified in source data")).strip() or "Not specified in source data",
				"how_to_apply": str(item.get("how_to_apply", "Not specified in source data")).strip() or "Not specified in source data",
			}
		)
	return normalized


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
				"brief_description": "Not specified in source data",
				"eligibility": "Not specified in source data",
				"how_to_apply": "Not specified in source data",
			}
		)
		if len(result) >= 5:
			break
	return result


def _clean_summary(text: str) -> str:
	"""Remove markdown bold/numbering for cleaner UI display."""
	text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)  # strip bold markers
	text = re.sub(r"^\s*\d+\.\s*", "• ", text, flags=re.MULTILINE)  # numbered lists to bullets
	text = re.sub(r"^\s*[-–]\s*", "• ", text, flags=re.MULTILINE)  # dash bullets to bullets
	return text.strip()


def _fallback_from_sources(location: str, sources: List[Dict[str, str]]) -> Dict[str, Any]:
	"""Fallback response when LLM enrichment is unavailable."""
	schemes: List[Dict[str, str]] = []
	for src in sources[:5]:
		title = (src.get("title") or "Government Scheme").strip()
		url = (src.get("url") or "").strip()
		domain = (src.get("domain") or "Official government source").strip()
		schemes.append(
			{
				"name": title,
				"brief_description": f"Relevant scheme information sourced from {domain}.",
				"eligibility": "Check official notification for eligibility details.",
				"how_to_apply": url or "Visit the official department portal listed in sources.",
			}
		)

	if not schemes:
		schemes = [
			{
				"name": "No schemes extracted",
				"brief_description": "Could not extract schemes from official sources at this time.",
				"eligibility": "Not specified in source data",
				"how_to_apply": "Try again later or check state agriculture department portals.",
			}
		]

	return {
		"summary": (
			f"Showing official-source scheme links for {location}. AI enrichment is temporarily unavailable, "
			"but you can still review and apply via the listed portals."
		),
		"schemes": schemes,
		"sources": sources,
		"llm_enhanced": False,
	}


if __name__ == "__main__":
	demo_user = {
		"location": "Madhya Pradesh",
		"crops": ["wheat", "soybean"],
		"acreage": "3 acres",
		"irrigation": "canal",
		"soil_type": "black soil",
	}
	print(generate_government_schemes(demo_user))
