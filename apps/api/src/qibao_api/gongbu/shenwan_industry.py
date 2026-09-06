"""申万行业统一映射层。

映射表可由运维导入；内置申万2021一级行业和稳定历史别名用于兼容数据源，
无法确认时返回待核验。
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from qibao_api.contracts.industry import (
    CanonicalIndustryAssignment,
    IndustryMappingEvidence,
    ShenwanIndustry,
)


DEFAULT_VERSION = "SW2021"
_DEFAULT_RESOLVER: "ShenwanIndustryResolver | None" = None

# 申万行业分类（2021版）一级行业，共31类。代码是稳定的规范主键，
# 所有下游聚合都应使用这里的 code/name，而不是直接使用数据源行业文本。
_SW2021_LEVEL_ONE: tuple[tuple[str, str], ...] = (
    ("SW801010", "农林牧渔"),
    ("SW801030", "基础化工"),
    ("SW801040", "钢铁"),
    ("SW801050", "有色金属"),
    ("SW801080", "电子"),
    ("SW801110", "家用电器"),
    ("SW801120", "食品饮料"),
    ("SW801130", "纺织服饰"),
    ("SW801140", "轻工制造"),
    ("SW801150", "医药生物"),
    ("SW801160", "公用事业"),
    ("SW801170", "交通运输"),
    ("SW801180", "房地产"),
    ("SW801200", "商贸零售"),
    ("SW801210", "社会服务"),
    ("SW801230", "综合"),
    ("SW801710", "建筑材料"),
    ("SW801720", "建筑装饰"),
    ("SW801730", "电力设备"),
    ("SW801740", "国防军工"),
    ("SW801750", "计算机"),
    ("SW801760", "传媒"),
    ("SW801770", "通信"),
    ("SW801780", "银行"),
    ("SW801790", "非银金融"),
    ("SW801880", "汽车"),
    ("SW801890", "机械设备"),
    ("SW801950", "煤炭"),
    ("SW801960", "石油石化"),
    ("SW801970", "环保"),
    ("SW801980", "美容护理"),
)
_SW2021_BY_CODE: dict[str, tuple[str, str, str]] = {
    code: (code, name, "一级") for code, name in _SW2021_LEVEL_ONE
}

# 数据源和旧版本常见行业名称。值始终指向申万2021一级规范名称。
_ALIASES: dict[str, tuple[str, str, str]] = {
    name: (code, name, "一级") for code, name in _SW2021_LEVEL_ONE
}
_ALIASES.update({
    "软件开发": ("SW801750", "计算机", "一级"),
    "IT服务": ("SW801750", "计算机", "一级"),
    "计算机应用": ("SW801750", "计算机", "一级"),
    "化工": ("SW801030", "基础化工", "一级"),
    "纺织服装": ("SW801130", "纺织服饰", "一级"),
    "商业贸易": ("SW801200", "商贸零售", "一级"),
    "休闲服务": ("SW801210", "社会服务", "一级"),
    "电气设备": ("SW801730", "电力设备", "一级"),
    "国防与装备": ("SW801740", "国防军工", "一级"),
    "证券": ("SW801790", "非银金融", "一级"),
    "保险": ("SW801790", "非银金融", "一级"),
    "采掘": ("SW801950", "煤炭", "一级"),
    "建筑": ("SW801720", "建筑装饰", "一级"),
    "公用事业": ("SW801160", "公用事业", "一级"),
})


class ShenwanIndustryResolver:
    def __init__(self, database: str | Path | None = None, *, version: str = DEFAULT_VERSION) -> None:
        self.version = version
        self.database = Path(database) if database else None
        if self.database:
            self.database.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self.database) as connection:
                connection.execute("""CREATE TABLE IF NOT EXISTS shenwan_industry_map (
                    source_system TEXT NOT NULL, source_code TEXT, source_name TEXT NOT NULL,
                    sw_code TEXT NOT NULL, sw_name TEXT NOT NULL, sw_level TEXT NOT NULL,
                    version TEXT NOT NULL, observed_at TEXT NOT NULL,
                    PRIMARY KEY(source_system, source_code, source_name, version)
                )""")

    def resolve(self, source_system: str, source_name: Any, source_code: Any = None, *, observed_at: datetime | None = None) -> CanonicalIndustryAssignment:
        observed = observed_at or datetime.now(timezone.utc)
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=timezone.utc)
        name = str(source_name or "").strip() or None
        if name and name.isdigit():
            name = None
        code = str(source_code or "").strip() or None
        if code and code in _SW2021_BY_CODE:
            sw_code, sw_name, sw_level = _SW2021_BY_CODE[code]
            return self._assignment(
                source_system, code, name, sw_code, sw_name, sw_level,
                self.version, "exact_code", observed,
            )
        if self.database and name:
            with sqlite3.connect(self.database) as connection:
                row = connection.execute(
                    "SELECT sw_code, sw_name, sw_level, version FROM shenwan_industry_map "
                    "WHERE source_system=? AND (source_code=? OR source_name=?) ORDER BY observed_at DESC LIMIT 1",
                    (source_system, code, name),
                ).fetchone()
            if row:
                return self._assignment(source_system, code, name, row[0], row[1], row[2], row[3], "manual", observed)
        alias = _ALIASES.get(name or "")
        if alias:
            return self._assignment(source_system, code, name, *alias, self.version, "alias", observed)
        return CanonicalIndustryAssignment(evidence=IndustryMappingEvidence(
            source_system=source_system, source_code=code, source_name=name,
            matched_by="unmapped", observed_at=observed,
        ))

    def _assignment(self, source_system: str, source_code: str | None, source_name: str | None,
                    sw_code: str, sw_name: str, sw_level: str, version: str,
                    matched_by: str, observed_at: datetime) -> CanonicalIndustryAssignment:
        return CanonicalIndustryAssignment(
            industry=ShenwanIndustry(code=sw_code, name=sw_name, level=sw_level, version=version),
            evidence=IndustryMappingEvidence(source_system=source_system, source_code=source_code,
                source_name=source_name, matched_by=matched_by, observed_at=observed_at),
        )


def resolve_shenwan_industry(source_name: Any, source_system: str = "unknown", source_code: Any = None,
                             *, observed_at: datetime | None = None) -> CanonicalIndustryAssignment:
    resolver = _DEFAULT_RESOLVER or ShenwanIndustryResolver()
    return resolver.resolve(source_system, source_name, source_code, observed_at=observed_at)


def configure_shenwan_resolver(database: str | Path, *, version: str = DEFAULT_VERSION) -> ShenwanIndustryResolver:
    global _DEFAULT_RESOLVER
    _DEFAULT_RESOLVER = ShenwanIndustryResolver(database, version=version)
    return _DEFAULT_RESOLVER
