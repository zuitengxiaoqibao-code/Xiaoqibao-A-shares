from __future__ import annotations

import hashlib
import re
from datetime import date, datetime

from qibao_api.contracts.company_research import LatestTipCategory, LatestTipItem, LatestTipTone


_DATE_RE = re.compile(r"(?P<year>20\d{2})[-/.年](?P<month>\d{1,2})[-/.月](?P<day>\d{1,2})日?(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?")
_LEADING_LABEL_RE = re.compile(r"^(?:[●◆■]\s*)?(?:最新提示|最新公告|最新报道|业绩预告|风险提示|公告|提示)\s*[:：]?\s*")
_PERCENT_RANGE_RE = re.compile(r"(?:变动幅度(?:为|是)?|同比(?:下降|减少|增长|增加)?)[^0-9%-]{0,24}(-?\d+(?:\.\d+)?%?\s*(?:-|~|～|至|到)\s*-?\d+(?:\.\d+)?%?)")
_PROFIT_RANGE_RE = re.compile(r"净利润[^\d-]{0,16}(-?\d+(?:\.\d+)?)\s*(?:万元|万|亿元)?\s*(?:至|-|~|～)\s*(-?\d+(?:\.\d+)?)")
_F10_HEADER_RE = re.compile(r"☆?\d{6}\s*[^\n|]{0,24}?更新日期[^\n|]*通达信(?:沪深京)?F10", re.IGNORECASE)
_F10_CATALOG_RE = re.compile(r"[★☆]?本栏包括(?:【\d+\.[^】]+】)+")
_CATALOG_ITEM_RE = re.compile(r"【\d+\.[^】]+】")
_TABLE_BORDER_RE = re.compile(r"[|｜┌┬┐├┼┤└┴┘─━═]{2,}")
_EMPTY_SECTION_RE = re.compile(r"(?:最新分红扩股|最新指标|最新提示)\s*[:：]\s*(?:[|｜;；\s]*)$")
_FINANCIAL_FIELD_TEMPLATE = r"{label}\s*[（(]?\s*(?P<unit>万元|亿元|元)?\s*[）)]?\s*[:：]?\s*(?P<value>-?\d+(?:\.\d+)?)"
_YOY_RE = re.compile(r"同比(?:增长|增减|变化)?\s*[（(]?\s*%?\s*[）)]?\s*[:：]?\s*(-?\d+(?:\.\d+)?)")
_NOISE_MARKERS = ("本栏包括", "互动问答", "最新主要指标", "每股收益", "每股净资产", "报告期", "加权净资产收益率", "总股本", "流通A股", "通达信沪深京F10")
_EVENT_MARKERS = ("公告", "合同", "协议", "签署", "中标", "合作", "业绩预告", "净利润", "营业收入", "风险", "诉讼", "仲裁", "处罚", "减持", "回购", "增持", "异动", "停牌", "复牌", "披露", "发布", "中报", "年报", "解禁")


def _normalize_date(match: re.Match[str]) -> str:
    return date(int(match.group("year")), int(match.group("month")), int(match.group("day"))).isoformat()


def _clean_evidence_text(value: str) -> str:
    text = str(value).replace("\r", " ").replace("\t", " ")
    text = _F10_HEADER_RE.sub(" ", text)
    text = _F10_CATALOG_RE.sub(" ", text)
    text = _CATALOG_ITEM_RE.sub(" ", text)
    text = _TABLE_BORDER_RE.sub(" ", text)
    text = re.sub(r"\s*[|｜]\s*", "；", text)
    text = re.sub(r"(?:；\s*){2,}", "；", text)
    text = re.sub(r"\s+", " ", text).strip(" ；|｜")
    return text


def _category(text: str) -> LatestTipCategory:
    if any(keyword in text for keyword in ("业绩预告", "预告业绩", "净利润", "归母净利润", "营业收入", "业绩快报")):
        return "业绩预告"
    if any(keyword in text for keyword in ("融资", "增发", "配股", "回购", "质押", "解禁", "减持", "限售股")):
        return "资金与融资"
    if any(keyword in text for keyword in ("风险", "诉讼", "仲裁", "违规", "警示", "问询", "担保")):
        return "风险提醒"
    if any(keyword in text for keyword in ("异动", "龙虎榜", "停牌", "复牌")):
        return "交易异动"
    if any(keyword in text for keyword in ("公告", "合同", "协议", "签署", "中标", "合作", "投资者关系")):
        return "公告与合同"
    return "其他"


def _is_decline(text: str) -> bool:
    if any(keyword in text for keyword in ("下降", "减少", "下滑", "亏损", "预亏")):
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
    text = _clean_evidence_text(raw_text)
    text = _LEADING_LABEL_RE.sub("", text).strip(" |;；")
    text = _DATE_RE.sub("", text, count=1).strip(" |;；，,:")
    return re.sub(r"\s+", " ", text)[:220] or _clean_evidence_text(raw_text)[:220]


def _is_noise(raw_text: str) -> bool:
    text = _clean_evidence_text(raw_text)
    if not text or _EMPTY_SECTION_RE.fullmatch(text):
        return True
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
        for title, keywords in (
            ("限售股解禁事项", ("解禁", "限售股上市流通")),
            ("股份回购事项", ("回购",)),
            ("股东减持事项", ("减持",)),
            ("定向增发事项", ("定增", "向特定对象发行", "非公开发行")),
            ("股权质押事项", ("质押",)),
            ("融资事项", ("融资", "配股")),
        ):
            if any(keyword in text for keyword in keywords):
                return title
        return "资本事项"
    return "原文待整理"


def _financial_field(text: str, label: str) -> tuple[str, str, str | None] | None:
    field_re = re.compile(_FINANCIAL_FIELD_TEMPLATE.format(label=re.escape(label)))
    match = field_re.search(text)
    if not match:
        return None
    tail = text[match.end():match.end() + 80]
    yoy_match = _YOY_RE.search(tail)
    return match.group("value"), match.group("unit") or "", yoy_match.group(1) if yoy_match else None


def _financial_snapshot(text: str) -> tuple[str | None, str, str, LatestTipTone, str] | None:
    revenue = _financial_field(text, "营业收入")
    profit = _financial_field(text, "净利润")
    if not revenue or not profit:
        return None
    date_match = _DATE_RE.search(text)
    parsed_date = _normalize_date(date_match) if date_match else None
    facts: list[str] = []
    yoy_values: list[float] = []
    for label, field in (("营业收入", revenue), ("净利润", profit)):
        value, unit, yoy = field
        fact = f"{label} {value}{f' {unit}' if unit else ''}"
        if yoy is not None:
            yoy_value = float(yoy)
            yoy_values.append(yoy_value)
            direction = "增长" if yoy_value >= 0 else "下降"
            fact += f"，同比{direction} {abs(yoy_value):g}%"
        facts.append(fact)
    if yoy_values and all(value > 0 for value in yoy_values):
        title, tone = "季度经营数据同比增长", "positive"
    elif yoy_values and all(value < 0 for value in yoy_values):
        title, tone = "季度经营数据同比下降", "risk"
    else:
        title, tone = "季度经营数据分化", "neutral"
    summary = "；".join(facts)
    raw = f"{parsed_date + '；' if parsed_date else ''}{summary}"
    return parsed_date, title, summary, tone, raw


def _event_segments(text: str) -> list[str]:
    bullet_segments = [segment for segment in re.split(r"(?=[●◆■])", text) if segment.lstrip().startswith(("●", "◆", "■"))]
    if bullet_segments:
        return bullet_segments
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines if len(lines) > 1 else [text]


def _make_item(
    *, raw_text: str, parsed_date: str | None, category: LatestTipCategory,
    tone: LatestTipTone, title: str, summary: str, source: str, observed_at: datetime | None,
) -> LatestTipItem:
    clean_raw = _clean_evidence_text(raw_text)
    digest = hashlib.sha256(f"{source}:{parsed_date or ''}:{clean_raw}".encode("utf-8")).hexdigest()[:16]
    return LatestTipItem(
        id=f"{source}:{digest}", category=category, title=title, date=parsed_date,
        tone=tone, summary=summary, source=source, observed_at=observed_at, raw_text=clean_raw,
    )


def parse_latest_tips(
    text: str | None,
    *,
    source: str,
    observed_at: datetime | None,
) -> tuple[LatestTipItem, ...]:
    if not text or not text.strip():
        return ()

    normalized = re.sub(r"[\r\t]+", " ", str(text)).strip()
    items: list[LatestTipItem] = []
    snapshot = _financial_snapshot(normalized)
    if snapshot:
        parsed_date, title, summary, tone, raw_text = snapshot
        items.append(_make_item(
            raw_text=raw_text, parsed_date=parsed_date, category="业绩预告", tone=tone,
            title=title, summary=summary, source=source, observed_at=observed_at,
        ))

    for raw_text in _event_segments(normalized):
        if _is_noise(raw_text):
            continue
        clean_raw = _clean_evidence_text(raw_text)
        match = _DATE_RE.search(clean_raw)
        parsed_date = _normalize_date(match) if match else None
        category = _category(clean_raw)
        tone = _tone(clean_raw, category)
        title = _event_title(clean_raw, category)
        summary = _summary(clean_raw)
        items.append(_make_item(
            raw_text=clean_raw, parsed_date=parsed_date, category=category, tone=tone,
            title=title, summary=summary, source=source, observed_at=observed_at,
        ))

    unique: dict[tuple[str | None, str, str], LatestTipItem] = {}
    for item in items:
        unique.setdefault((item.date, item.title, item.summary), item)
    return tuple(unique.values())
