from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from qibao_api.contracts.company_research import LatestTipCategory, LatestTipItem, LatestTipTone


_DATE_RE = re.compile(r"(?P<year>20\d{2})[-/.年](?P<month>\d{1,2})[-/.月](?P<day>\d{1,2})日?(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?")
_SPLIT_RE = re.compile(r"\s*(?:\|+|\n+)\s*")
_LEADING_LABEL_RE = re.compile(r"^(?:[●◆■]\s*)?(?:最新提示|最新公告|业绩预告|风险提示|公告|提示)\s*[:：]?\s*")
_PERCENT_RANGE_RE = re.compile(r"(?:变动幅度(?:为|是)?|同比(?:下降|减少|增长|增加)?)[^0-9%-]{0,24}(-?\d+(?:\.\d+)?%?\s*(?:-|~|～|至|到)\s*-?\d+(?:\.\d+)?%?)")
_PROFIT_RANGE_RE = re.compile(r"净利润[^\d-]{0,16}(-?\d+(?:\.\d+)?)\s*(?:万元|万|亿元)?\s*(?:至|-|~|～)\s*(-?\d+(?:\.\d+)?)")
_NOISE_MARKERS = ("本栏包括", "互动问答", "最新主要指标", "每股收益", "每股净资产", "报告期", "加权净资产收益率", "总股本", "流通A股")
_EVENT_MARKERS = ("公告", "合同", "协议", "签署", "中标", "合作", "业绩预告", "净利润", "风险", "诉讼", "仲裁", "处罚", "减持", "回购", "增持", "异动", "停牌", "复牌", "披露", "发布", "中报", "年报")


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


def _is_decline(text: str) -> bool:
    if any(keyword in text for keyword in ("下降", "减少", "下滑", "亏损", "预亏", "负")):
        return True
    percent_match = _PERCENT_RANGE_RE.search(text)
    if percent_match and "-" in percent_match.group(1):
        return True
    profit_match = _PROFIT_RANGE_RE.search(text)
    if profit_match:
        return float(profit_match.group(2)) < float(profit_match.group(1))
    return False


def _tone(text: str, category: LatestTipCategory) -> LatestTipTone:
    if category == "风险提醒":
        return "risk"
    if _is_decline(text) or any(keyword in text for keyword in ("不及预期", "风险")):
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


def _is_noise(raw_text: str) -> bool:
    text = raw_text.strip()
    if len(text) < 8 and not any(marker in text for marker in _EVENT_MARKERS):
        return True
    if _DATE_RE.fullmatch(text.strip("●◆■ ")):
        return True
    if any(marker in text for marker in _NOISE_MARKERS):
        return not _DATE_RE.search(text) or not any(marker in text for marker in _EVENT_MARKERS)
    if not _DATE_RE.search(text) and not any(marker in text for marker in _EVENT_MARKERS):
        return True
    return False


def _event_title(text: str, category: LatestTipCategory) -> str:
    summary = _summary(text)
    if category == "业绩预告":
        percent_match = _PERCENT_RANGE_RE.search(text)
        if percent_match:
            percent_range = percent_match.group(1).replace("-", "～").replace("~", "～")
            direction = "下降" if _is_decline(text) else "增长"
            return f"净利润预计同比{direction} {percent_range}"
        return "净利润预计下降" if _is_decline(text) else "净利润业绩预告"
    if category == "风险提醒":
        for title, keywords in (("交易风险提示", ("交易风险", "风险提示")), ("减持风险", ("减持",)), ("诉讼或仲裁风险", ("诉讼", "仲裁")), ("监管风险", ("处罚", "违规", "警示"))):
            if any(keyword in text for keyword in keywords):
                return title
        return "风险提示"
    if category == "公告与合同":
        if "债券" in text and "无异议" in text:
            return "公司债券挂牌转让获无异议"
        if "战略合作协议" in text:
            return "签署战略合作协议"
        if "签署" in text and "协议" in text:
            return "签署合作协议"
        if "中标" in text or "订单" in text:
            return "获得订单或中标"
        return summary[:28].rstrip("，。；") or "重大公告"
    if category == "交易异动":
        return "交易异动提示"
    if category == "资金与融资":
        return "资金事项"
    return "原文待整理"


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
        if _is_noise(raw_text):
            continue
        match = _DATE_RE.search(raw_text)
        parsed_date = _normalize_date(match) if match else None
        category = _category(raw_text)
        tone = _tone(raw_text, category)
        title = _event_title(raw_text, category)
        summary = _summary(raw_text)
        digest = hashlib.sha256(f"{source}:{parsed_date or ''}:{raw_text}".encode("utf-8")).hexdigest()[:16]
        items.append(LatestTipItem(
            id=f"{source}:{digest}", category=category, title=title, date=parsed_date,
            tone=tone, summary=summary, source=source, observed_at=observed_at,
            raw_text=raw_text,
        ))
    return tuple(items)
