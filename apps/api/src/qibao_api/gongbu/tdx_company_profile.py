import re
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Any

from qibao_api.contracts.company_research import CompanyProfileEvidence
from qibao_api.gongbu.tdx_latest_tips import parse_latest_tips
from qibao_api.gongbu.tdx_client import TdxOperationError, create_tdx_client


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text[:1200] if text else None


def _extract_section(value: Any, category: str) -> str | None:
    if isinstance(value, Mapping):
        return _clean(value.get(category))
    return _clean(value)


class TdxCompanyProfileSource:
    def __init__(
        self,
        client_factory: Callable[[], Any] = create_tdx_client,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self.client_factory = client_factory
        self.clock = clock

    def fetch(self, symbol: str) -> CompanyProfileEvidence:
        client = self.client_factory()
        values: dict[str, str | None] = {}
        reasons: list[str] = []
        categories = {
            "company_overview": "公司概况",
            "industry_analysis": "行业分析",
            "latest_tips": "最新提示",
        }
        try:
            for field, category in categories.items():
                try:
                    values[field] = _extract_section(
                        client.F10(symbol=symbol, name=category),
                        category,
                    )
                    if values[field] is None:
                        reasons.append(f"通达信F10未返回{category}")
                except TdxOperationError:
                    values[field] = None
                    reasons.append(f"通达信节点未提供{category}")
                except Exception as error:
                    values[field] = None
                    reasons.append(f"通达信F10读取{category}失败：{error}")
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                close()
        available = sum(value is not None for value in values.values())
        status = "ready" if available == len(categories) else "partial" if available else "unavailable"
        latest_tip_items = parse_latest_tips(
            values.get("latest_tips"), source="mootdx-f10", observed_at=self.clock() if available else None,
        )
        return CompanyProfileEvidence(
            status=status,
            company_overview=values.get("company_overview"),
            industry_analysis=values.get("industry_analysis"),
            latest_tips=values.get("latest_tips"),
            latest_tip_items=latest_tip_items,
            source="mootdx-f10",
            observed_at=self.clock() if available else None,
            reasons=tuple(reasons),
        )
