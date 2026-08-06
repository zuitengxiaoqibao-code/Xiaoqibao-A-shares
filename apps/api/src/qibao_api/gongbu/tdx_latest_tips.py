from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from qibao_api.contracts.company_research import LatestTipCategory, LatestTipItem, LatestTipTone


_DATE_RE = re.compile(r"(?P<year>20\d{2})[-/.年](?P<month>\d{1,2})[-/.月](?P<day>\d{1,2})日?(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?")
_SPLIT_RE = re.compile(r"\s*(?:\|+|\n+)\s*")
_LEADING_LABEL_RE = re.compile(r"^(?:[●◆■]\s*)?(?:最新提示|最新公告|业绩预告|风险提示|公告|提示)\s*[:：]?\s*")


def _normalize_date(match: re.Match[str]) -> str:
    return date(int(match.group("year")), int(match.group("month")), int(match.group("day"))).isoformat()


def _category(text: str) -> LatestTipCategory:
    if any(keyword in text for keyword in ("业绩预告", "预告业绩", "净利润", "归母净利润", "营业收入", "业绩快报")):
        return "业绩预告"
    if any(keyword in text for keyword in ("融资", "增发", "配股", "回购", "质押", "解禁", "减持")):
        return "资金与融资"
    if any(keyword in text for keyword in ("风险", "诉讼", "仲裁", "违规", "警示", "问询", "担保")):
        return "风险提醒"
    if any(keyword in text for keyword in ("异动", "龙虎榜", "停牌", "复牌")):
        return "交易异动"
    if any(keyword in text for keyword in ("公告", "合同", "协议", "签署", "中标", "合作", "投资者关系")):
        return "公告与合同"
    return "其他"


def _tone(text: str, category: LatestTipCategory) -> LatestTipTone:
    if category == "风险提醒":
        return "risk"
    if any(keyword in text for keyword in ("下降", "下滑", "亏损", "预亏", "减少", "不及预期", "风险")):
        return "risk"
    if any(keyword in text for keyword in ("增长", "上升", "预增", "扭亏", "盈利", "中标", "合作协议", "回购")):
        return "positive"
    if category == "其他":
        return "unknown"
    return "neutral"


def _summary(raw_text: str) -> str:
    text = _LEADING_LABEL_RE.sub("", raw_text).strip(" |;")
    text = _DATE_RE.sub("", text, count=1).strip(" |;，,:")
    return re.sub(r"\s+", " ", text)[:220] or raw_text[:220]


def parse_latest_tips(
    text: str | None,
    *,
    source: str,
    observed_at: datetime | None,
) -> tuple[LatestTipItem, ...]:
    if not text or not text.strip():
        return ()

    normalized = re.sub(r"[\r\t]+", " ", str(text)).strip()
    raw_segments: list[str] = []
    for chunk in _SPLIT_RE.split(normalized):
        raw_segments.extend(segment.strip() for segment in re.split(r"(?=[●◆■])", chunk) if segment.strip())
    items: list[LatestTipItem] = []
    for raw_text in raw_segments:
        match = _DATE_RE.search(raw_text)
        parsed_date = _normalize_date(match) if match else None
        category = _category(raw_text)
        tone = _tone(raw_text, category)
        title = category if category != "其他" else "原文待整理"
        summary = _summary(raw_text)
        digest = hashlib.sha256(f"{source}:{parsed_date or ''}:{raw_text}".encode("utf-8")).hexdigest()[:16]
        items.append(LatestTipItem(
            id=f"{source}:{digest}", category=category, title=title, date=parsed_date,
            tone=tone, summary=summary, source=source, observed_at=observed_at,
            raw_text=raw_text,
        ))
    return tuple(items)
