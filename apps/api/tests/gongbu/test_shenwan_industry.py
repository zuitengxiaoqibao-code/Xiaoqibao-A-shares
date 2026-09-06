from datetime import datetime, timezone

import pytest

from qibao_api.gongbu.shenwan_industry import ShenwanIndustryResolver


@pytest.mark.parametrize(
    ("name", "code"),
    [
        ("农林牧渔", "SW801010"),
        ("基础化工", "SW801030"),
        ("钢铁", "SW801040"),
        ("有色金属", "SW801050"),
        ("电子", "SW801080"),
        ("家用电器", "SW801110"),
        ("食品饮料", "SW801120"),
        ("纺织服饰", "SW801130"),
        ("轻工制造", "SW801140"),
        ("医药生物", "SW801150"),
        ("公用事业", "SW801160"),
        ("交通运输", "SW801170"),
        ("房地产", "SW801180"),
        ("商贸零售", "SW801200"),
        ("社会服务", "SW801210"),
        ("综合", "SW801230"),
        ("建筑材料", "SW801710"),
        ("建筑装饰", "SW801720"),
        ("电力设备", "SW801730"),
        ("国防军工", "SW801740"),
        ("计算机", "SW801750"),
        ("传媒", "SW801760"),
        ("通信", "SW801770"),
        ("银行", "SW801780"),
        ("非银金融", "SW801790"),
        ("汽车", "SW801880"),
        ("机械设备", "SW801890"),
        ("煤炭", "SW801950"),
        ("石油石化", "SW801960"),
        ("环保", "SW801970"),
        ("美容护理", "SW801980"),
    ],
)
def test_all_sw2021_level_one_names_resolve_to_canonical_industry(name: str, code: str) -> None:
    result = ShenwanIndustryResolver().resolve(
        "eastmoney", name, observed_at=datetime(2026, 9, 3, tzinfo=timezone.utc)
    )
    assert result.is_verified
    assert result.industry is not None
    assert result.industry.code == code
    assert result.industry.name == name
    assert result.industry.level == "一级"
    assert result.industry.version == "SW2021"
    assert result.evidence.source_system == "eastmoney"


@pytest.mark.parametrize(
    ("source_name", "code", "canonical_name"),
    [
        ("软件开发", "SW801750", "计算机"),
        ("IT服务", "SW801750", "计算机"),
        ("化工", "SW801030", "基础化工"),
        ("纺织服装", "SW801130", "纺织服饰"),
        ("商业贸易", "SW801200", "商贸零售"),
        ("休闲服务", "SW801210", "社会服务"),
        ("电气设备", "SW801730", "电力设备"),
        ("国防与装备", "SW801740", "国防军工"),
        ("证券", "SW801790", "非银金融"),
        ("保险", "SW801790", "非银金融"),
        ("采掘", "SW801950", "煤炭"),
    ],
)
def test_common_source_aliases_resolve_to_sw2021_level_one_industry(
    source_name: str, code: str, canonical_name: str
) -> None:
    result = ShenwanIndustryResolver().resolve("legacy", source_name)

    assert result.is_verified
    assert result.industry is not None
    assert result.industry.code == code
    assert result.industry.name == canonical_name


def test_unknown_source_name_is_unmapped_and_cannot_be_formal_industry() -> None:
    result = ShenwanIndustryResolver().resolve(
        "tdx", "自定义概念", observed_at=datetime(2026, 9, 3, tzinfo=timezone.utc)
    )
    assert not result.is_verified
    assert result.industry is None
    assert result.evidence.matched_by == "unmapped"


def test_unmapped_assignment_exposes_pending_display_state() -> None:
    result = ShenwanIndustryResolver().resolve("tdx", "自定义概念")

    assert result.industry is None
    assert result.is_verified is False
    assert result.evidence.matched_by == "unmapped"


def test_database_mapping_is_preferred_and_retains_source_evidence(tmp_path) -> None:
    resolver = ShenwanIndustryResolver(tmp_path / "taxonomy.sqlite3")
    with resolver.database.open("ab"):
        pass
    import sqlite3
    with sqlite3.connect(resolver.database) as connection:
        connection.execute(
            "INSERT INTO shenwan_industry_map VALUES (?,?,?,?,?,?,?,?)",
            ("eastmoney", "1238", "软件开发", "SW801750", "计算机", "一级", "SW2021", "2026-09-03T00:00:00+00:00"),
        )
    result = resolver.resolve("eastmoney", "软件开发", "1238")
    assert result.is_verified
    assert result.industry is not None
    assert result.industry.code == "SW801750"
    assert result.industry.name == "计算机"
    assert result.evidence.matched_by == "manual"
