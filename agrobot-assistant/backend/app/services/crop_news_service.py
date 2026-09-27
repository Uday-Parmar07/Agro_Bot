import json
import re
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.database.schemas import CropMarketNews
from app.services import government_api_service


MARKET_NEWS_DOMAINS = [
    "gov.in",
    "nic.in",
    "pib.gov.in",
    "agmarknet.gov.in",
    "data.gov.in",
    "agricoop.nic.in",
    "commerce.gov.in",
    "dgft.gov.in",
    "apeda.gov.in",
    "imd.gov.in",
]

NO_NEWS_SENTINEL = "__NO_RELEVANT_MARKET_NEWS__"


class CropNewsService:
    def get_or_fetch_news(
        self,
        db: Session,
        crop: str,
        date_value: Optional[date] = None,
    ) -> dict[str, Any]:
        target_date = date_value or date.today()
        cached = self._cached_news(db, crop, target_date)
        if cached:
            return self._response(crop, target_date, cached)

        sources = self._search_market_news(crop)
        insights = self._summarize_market_news(crop, sources)
        saved = self._save_news(db, crop, target_date, insights)
        db.commit()
        return self._response(crop, target_date, saved)

    def _cached_news(self, db: Session, crop: str, cached_for_date: date) -> list[CropMarketNews]:
        return (
            db.query(CropMarketNews)
            .filter(
                CropMarketNews.crop.ilike(crop),
                CropMarketNews.cached_for_date == cached_for_date,
            )
            .order_by(CropMarketNews.id.asc())
            .all()
        )

    def _search_market_news(self, crop: str) -> list[dict[str, str]]:
        if government_api_service.tavily is None:
            return []

        queries = [
            f"{crop} mandi price market arrival MSP export policy India latest",
            f"{crop} commodity price movement mandi glut shortage weather India",
        ]
        all_results: list[dict[str, Any]] = []
        for query in queries:
            try:
                result = government_api_service.tavily.search(
                    query=query,
                    include_domains=MARKET_NEWS_DOMAINS,
                    max_results=8,
                    search_depth="advanced",
                )
            except Exception:
                try:
                    result = government_api_service.tavily.search(
                        query=query,
                        include_domains=MARKET_NEWS_DOMAINS,
                        max_results=6,
                        search_depth="basic",
                    )
                except Exception:
                    result = {}
            all_results.extend(result.get("results", []))

        seen_urls = set()
        sources = []
        for item in all_results:
            url = (item.get("url") or "").strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            sources.append(
                {
                    "title": (item.get("title") or url).strip(),
                    "url": url,
                    "content": (item.get("content") or "").strip(),
                    "published_date": item.get("published_date") or item.get("published_at") or "",
                }
            )
        return sources[:10]

    def _summarize_market_news(self, crop: str, sources: list[dict[str, str]]) -> list[dict[str, Any]]:
        if not sources:
            return []

        if government_api_service.groq_client is None:
            return self._fallback_from_sources(crop, sources)

        source_text = "\n\n".join(
            f"[{source.get('title')}] {source.get('content')} ({source.get('url')})"
            for source in sources
            if source.get("content")
        )
        prompt = f"""
You summarize Indian crop market news for farmers.
Use only the supplied source snippets.
Crop: {crop}

Source snippets:
{source_text}

Return ONLY valid JSON:
{{
  "insights": [
    {{
      "headline": "short factual headline",
      "summary": "1-2 short sentences explaining the price-moving event",
      "source_url": "source URL from snippets"
    }}
  ]
}}

Rules:
- Include 3 to 5 insights if source data supports them.
- Focus on price-moving events: MSP, export/import policy, mandi glut or shortage, arrivals, weather disruption.
- Do not invent news, numbers, or URLs.
- If no relevant market insight exists, return {{"insights":[]}}.
"""
        try:
            completion = government_api_service.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=900,
            )
            raw = completion.choices[0].message.content
            parsed = self._parse_llm_response(raw)
            return self._normalize_insights(parsed.get("insights", []), sources)
        except Exception:
            return self._fallback_from_sources(crop, sources)

    def _parse_llm_response(self, raw_text: str) -> dict[str, Any]:
        cleaned = (raw_text or "").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end > start:
                try:
                    return json.loads(cleaned[start : end + 1])
                except json.JSONDecodeError:
                    return {"insights": []}
        return {"insights": []}

    def _normalize_insights(
        self,
        items: list[dict[str, Any]],
        sources: list[dict[str, str]],
    ) -> list[dict[str, Any]]:
        source_by_url = {source.get("url"): source for source in sources}
        normalized = []
        seen = set()
        for item in items:
            headline = self._clean_text(item.get("headline"), max_len=140)
            summary = self._clean_text(item.get("summary"), max_len=320)
            source_url = str(item.get("source_url") or "").strip()
            if not headline or not summary:
                continue
            if source_url and source_url not in source_by_url:
                source_url = ""
            if not source_url and sources:
                source_url = sources[0].get("url", "")
            key = headline.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(
                {
                    "headline": headline,
                    "summary": summary,
                    "source_url": source_url,
                    "published_or_found_at": self._parse_datetime(
                        source_by_url.get(source_url, {}).get("published_date")
                    ),
                }
            )
            if len(normalized) == 5:
                break
        return normalized

    def _fallback_from_sources(self, crop: str, sources: list[dict[str, str]]) -> list[dict[str, Any]]:
        insights = []
        patterns = [
            r"\bmsp\b",
            r"\bexport\b",
            r"\bimport\b",
            r"\bprice\b",
            r"\bmandi\b",
            r"\barrival",
            r"\bshortage\b",
            r"\bweather\b",
            r"\brain\b",
        ]
        for source in sources:
            content = source.get("content") or ""
            lower = content.lower()
            if not any(re.search(pattern, lower) for pattern in patterns):
                continue
            headline = self._clean_text(source.get("title") or f"{crop} market update", max_len=140)
            summary = self._clean_text(content, max_len=260)
            if headline and summary:
                insights.append(
                    {
                        "headline": headline,
                        "summary": summary,
                        "source_url": source.get("url", ""),
                        "published_or_found_at": self._parse_datetime(source.get("published_date")),
                    }
                )
            if len(insights) == 5:
                break
        return insights

    def _save_news(
        self,
        db: Session,
        crop: str,
        cached_for_date: date,
        insights: list[dict[str, Any]],
    ) -> list[CropMarketNews]:
        if not insights:
            insights = [
                {
                    "headline": NO_NEWS_SENTINEL,
                    "summary": "No relevant market news found today.",
                    "source_url": None,
                    "published_or_found_at": datetime.utcnow(),
                }
            ]

        saved = []
        for insight in insights:
            headline = insight.get("headline")
            if not headline:
                continue
            existing = (
                db.query(CropMarketNews)
                .filter(
                    CropMarketNews.crop.ilike(crop),
                    CropMarketNews.cached_for_date == cached_for_date,
                    CropMarketNews.headline == headline,
                )
                .first()
            )
            if existing:
                saved.append(existing)
                continue
            row = CropMarketNews(
                crop=crop,
                headline=headline,
                summary=insight.get("summary") or "",
                source_url=insight.get("source_url"),
                published_or_found_at=insight.get("published_or_found_at") or datetime.utcnow(),
                cached_for_date=cached_for_date,
            )
            db.add(row)
            db.flush()
            saved.append(row)
        return saved

    def _response(
        self,
        crop: str,
        cached_for_date: date,
        rows: list[CropMarketNews],
    ) -> dict[str, Any]:
        return {
            "crop": crop,
            "cached_for_date": cached_for_date,
            "insights": [row for row in rows if row.headline != NO_NEWS_SENTINEL],
            "data_status": "available" if any(row.headline != NO_NEWS_SENTINEL for row in rows) else "no_news",
        }

    def _clean_text(self, value: Any, max_len: int) -> str:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        if len(text) <= max_len:
            return text
        return text[: max_len - 1].rstrip() + "..."

    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        if isinstance(value, datetime):
            return value
        if not value:
            return None
        text = str(value).strip()
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                parsed = datetime.strptime(text, fmt)
                return parsed.replace(tzinfo=None)
            except ValueError:
                continue
        return None


crop_news_service = CropNewsService()
