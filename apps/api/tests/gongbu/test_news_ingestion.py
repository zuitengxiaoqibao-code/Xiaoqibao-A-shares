import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
import pytest

from qibao_api.contracts.market import AssetKind
from qibao_api.contracts.news import NewsArticle
from qibao_api.gongbu.news_ingestion import NewsIngestionService
from qibao_api.gongbu.news_linking import DeterministicNewsLinker
from qibao_api.gongbu.news_repository import NewsRepository
from qibao_api.operations.realtime_snapshot_bus import RealtimeSnapshotBus
from qibao_api.libu_compliance.repository import ComplianceRepository
from qibao_api.contracts.risk import ComplianceRecord
from qibao_api.settings_repository import (
    AISettings,
    AISettingsRepository,
    EffectiveAISettingsResolver,
)
from qibao_api.zhongshu.news_ai import (
    NewsAIGateway,
    ReloadableNewsAIGateway,
)


NOW = datetime(2026, 7, 14, 1, 0, tzinfo=UTC)


class Source:
    async def fetch(self):
        import hashlib

        raw = b"600000 policy news"
        return [NewsArticle(
            article_id="news-1", canonical_url="https://news.example/1",
            publisher="测试来源", title="600000获得支持政策",
            summary="先进制造专项政策。", published_at=NOW, fetched_at=NOW,
            content_hash=hashlib.sha256(raw).hexdigest(), raw_snapshot=raw,
            source_verified=True,
        )]


class UnavailableProvider:
    async def complete(self, _request):
        raise OSError("model offline")


class RefetchedSource:
    def __init__(self) -> None:
        self.fetch_count = 0

    async def fetch(self):
        import hashlib

        self.fetch_count += 1
        raw = f"600000 policy news poll {self.fetch_count}".encode()
        return [NewsArticle(
            article_id="news-stable", canonical_url="https://news.example/stable",
            publisher="测试来源", title="600000获得支持政策",
            summary="先进制造专项政策。", published_at=NOW,
            fetched_at=NOW + timedelta(minutes=self.fetch_count),
            content_hash=hashlib.sha256(b"stable semantic content").hexdigest(),
            raw_snapshot=raw, source_verified=True,
        )]


class StockSource:
    def __init__(self, *, explicit: bool = True) -> None:
        self.symbols = []
        self.explicit = explicit

    async def fetch(self, symbol):
        import hashlib

        self.symbols.append(symbol)
        raw = f"stock-news-{symbol}-{self.explicit}".encode()
        summary = f"{symbol} 公司发布公告" if self.explicit else "搜索结果未提及该股票"
        return [NewsArticle(
            article_id=f"stock-{symbol}-{self.explicit}",
            canonical_url="https://finance.eastmoney.com/a/stock.html",
            publisher="测试来源", title="个股新闻", summary=summary,
            published_at=NOW, fetched_at=NOW,
            content_hash=hashlib.sha256(raw).hexdigest(), raw_snapshot=raw,
            source_verified=True,
        )]


class ManySource:
    async def fetch(self):
        import hashlib

        topics = (
            "600000 annual report profit expansion",
            "600000 board member resignation",
            "600000 factory capacity expansion",
            "600000 product safety recall",
            "600000 dividend distribution plan",
            "600000 regulatory investigation notice",
            "600000 patent approval milestone",
            "600000 overseas contract signed",
            "600000 shareholder reduction filing",
            "600000 merger restructuring progress",
            "600000 credit rating adjustment",
        )
        return [NewsArticle(
            article_id=f"news-many-{index}",
            canonical_url=f"https://news.example/many/{index}",
            publisher="测试来源",
            title=topics[index],
            summary="先进制造专项政策。",
            published_at=NOW,
            fetched_at=NOW,
            content_hash=hashlib.sha256(f"many-{index}".encode()).hexdigest(),
            raw_snapshot=f"many-{index}".encode(),
            source_verified=True,
        ) for index in range(11)]


def ai_response(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content)
    prompt = json.loads(body["messages"][1]["content"])
    citation_id = prompt["allowed_citation_ids"][0]
    content = json.dumps({
        "statements": [{
            "statement_id": f"statement-{citation_id}",
            "kind": "fact",
            "text": prompt["event"]["headline"],
            "citation_ids": [citation_id],
        }],
        "impact_direction": "neutral",
        "confidence": "0.70",
        "contrary_citation_ids": [],
    }, ensure_ascii=False)
    return httpx.Response(200, json={
        "choices": [{"message": {"content": content}}],
    })


def authorize(repository: ComplianceRepository) -> None:
    repository.append_record(ComplianceRecord(
        record_id="news-eastmoney", asset=AssetKind.A_SHARE, source="eastmoney",
        permission_state="authorized", permission_reference="test",
        disclaimer_version="2026-07", user_acknowledged_at=NOW, recorded_at=NOW,
    ))


@pytest.mark.asyncio
async def test_ingestion_requires_authorization_and_persists_complete_chain(tmp_path) -> None:
    compliance = ComplianceRepository(tmp_path / "compliance.sqlite3")
    compliance.set_feature_sources("market_news", AssetKind.A_SHARE, ("eastmoney",))
    repository = NewsRepository(tmp_path / "news.sqlite3")
    bus = RealtimeSnapshotBus()
    service = NewsIngestionService(
        Source(), repository,
        DeterministicNewsLinker(
            instrument_aliases={},
            industry_keywords={"高端制造": ("先进制造",)},
            theme_keywords={"政策支持": ("支持政策", "专项政策")},
        ),
        compliance,
        NewsAIGateway(
            UnavailableProvider(), provider_name="unconfigured", model="none",
            prompt_version="news-v1", clock=lambda: NOW,
        ),
        realtime_snapshot_bus=bus,
    )

    with pytest.raises(Exception, match="eastmoney"):
        await service.sync()

    authorize(compliance)
    result = await service.sync()

    assert result == {
        "fetched": 1, "inserted": 1, "clusters": 1, "events": 1,
        "interpretations": 1,
    }
    assert repository.articles()[0].article_id == "news-1"
    assert repository.events()[0].affected_instruments == (
        (AssetKind.A_SHARE, "600000"),
    )
    assert repository.interpretations()[0].degraded is True
    assert bus.latest("news_events")["payload"]["verified_count"] == 1
    assert (await service.sync())["inserted"] == 0
    assert len(repository.interpretations()) == 1
    repository.close()
    compliance.close()


@pytest.mark.asyncio
async def test_ingestion_reuses_the_first_snapshot_for_a_refetched_article(tmp_path) -> None:
    compliance = ComplianceRepository(tmp_path / "compliance.sqlite3")
    compliance.set_feature_sources("market_news", AssetKind.A_SHARE, ("eastmoney",))
    authorize(compliance)
    repository = NewsRepository(tmp_path / "news.sqlite3")
    service = NewsIngestionService(
        RefetchedSource(),
        repository,
        DeterministicNewsLinker(
            instrument_aliases={}, industry_keywords={}, theme_keywords={}
        ),
        compliance,
    )

    first = await service.sync()
    second = await service.sync()

    assert first["events"] == 1
    assert second["inserted"] == 0
    assert second["events"] == 0
    assert repository.articles()[0].raw_snapshot == b"600000 policy news poll 1"
    assert repository.events()[0].normalized_at == NOW + timedelta(minutes=1)
    repository.close()
    compliance.close()


@pytest.mark.asyncio
async def test_ingestion_records_taxonomy_rule_changes_as_an_idempotent_correction(
    tmp_path,
) -> None:
    compliance = ComplianceRepository(tmp_path / "compliance.sqlite3")
    compliance.set_feature_sources("market_news", AssetKind.A_SHARE, ("eastmoney",))
    authorize(compliance)
    repository = NewsRepository(tmp_path / "news.sqlite3")
    source = Source()
    legacy = NewsIngestionService(
        source,
        repository,
        DeterministicNewsLinker(
            instrument_aliases={},
            industry_keywords={"legacy-industry": ("先进制造",)},
            theme_keywords={},
        ),
        compliance,
    )
    current = NewsIngestionService(
        source,
        repository,
        DeterministicNewsLinker(
            instrument_aliases={}, industry_keywords={}, theme_keywords={}
        ),
        compliance,
    )

    await legacy.sync()
    second = await current.sync()
    third = await current.sync()

    assert second["events"] == 0
    assert third["events"] == 0
    assert repository.events()[0].industries == ("legacy-industry",)
    assert repository.effective_events()[0].industries == ()
    assert len(repository.corrections()) == 1
    assert repository.corrections()[0].origin == "system"
    repository.close()
    compliance.close()


@pytest.mark.asyncio
async def test_symbol_ingestion_uses_query_context_for_verified_association(tmp_path) -> None:
    compliance = ComplianceRepository(tmp_path / "compliance.sqlite3")
    compliance.set_feature_sources("market_news", AssetKind.A_SHARE, ("eastmoney",))
    authorize(compliance)
    repository = NewsRepository(tmp_path / "news.sqlite3")
    explicit = StockSource(explicit=False)
    linker = DeterministicNewsLinker(
        instrument_aliases={}, industry_keywords={}, theme_keywords={}
    )
    service = NewsIngestionService(
        Source(), repository, linker, compliance, stock_source=explicit
    )

    result = await service.sync_symbol("600519")

    assert result["fetched"] == 1
    assert explicit.symbols == ["600519"]
    assert repository.events_for_symbol("600519")[0].review_state == "verified"
    event = repository.events()[0]
    assert event.affected_instruments == ((AssetKind.A_SHARE, "600519"),)
    assert event.association_confidence == Decimal("0.85")
    repository.close()
    compliance.close()


@pytest.mark.asyncio
async def test_refetched_degraded_event_is_upgraded_once_after_ai_configuration(
    tmp_path,
) -> None:
    compliance = ComplianceRepository(tmp_path / "compliance.sqlite3")
    compliance.set_feature_sources("market_news", AssetKind.A_SHARE, ("eastmoney",))
    authorize(compliance)
    repository = NewsRepository(tmp_path / "news.sqlite3")
    source = Source()
    linker = DeterministicNewsLinker(
        instrument_aliases={}, industry_keywords={}, theme_keywords={}
    )
    degraded_service = NewsIngestionService(
        source,
        repository,
        linker,
        compliance,
        NewsAIGateway(
            UnavailableProvider(), provider_name="unconfigured", model="none",
            prompt_version="news-v1", clock=lambda: NOW,
        ),
    )
    await degraded_service.sync()
    assert repository.interpretations()[0].degraded is True

    settings = AISettingsRepository(tmp_path / "settings")
    settings.save(AISettings(
        base_url="https://provider.example/v1",
        model="configured-model",
        api_key="secret-value",
    ))
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return ai_response(request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    configured_service = NewsIngestionService(
        source,
        repository,
        linker,
        compliance,
        ReloadableNewsAIGateway(
            EffectiveAISettingsResolver(settings), client=client, clock=lambda: NOW,
        ),
    )

    second = await configured_service.sync()
    third = await configured_service.sync()

    assert second["inserted"] == 0
    assert second["interpretations"] == 1
    assert third["interpretations"] == 0
    assert calls == 1
    assert len(repository.interpretations()) == 2
    assert repository.interpretations()[-1].degraded is False
    await client.aclose()
    repository.close()
    compliance.close()


@pytest.mark.asyncio
async def test_ingestion_limits_configured_ai_interpretations_to_ten_per_sync(
    tmp_path,
) -> None:
    compliance = ComplianceRepository(tmp_path / "compliance.sqlite3")
    compliance.set_feature_sources("market_news", AssetKind.A_SHARE, ("eastmoney",))
    authorize(compliance)
    repository = NewsRepository(tmp_path / "news.sqlite3")
    settings = AISettingsRepository(tmp_path / "settings")
    settings.save(AISettings(
        base_url="https://provider.example/v1",
        model="configured-model",
        api_key="secret-value",
    ))
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return ai_response(request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = NewsIngestionService(
        ManySource(),
        repository,
        DeterministicNewsLinker(
            instrument_aliases={}, industry_keywords={}, theme_keywords={}
        ),
        compliance,
        ReloadableNewsAIGateway(
            EffectiveAISettingsResolver(settings), client=client, clock=lambda: NOW,
        ),
        max_ai_interpretations_per_sync=10,
    )

    first = await service.sync()
    second = await service.sync()

    assert first["events"] == 11
    assert first["interpretations"] == 10
    assert second["interpretations"] == 1
    assert calls == 11
    assert len(repository.interpretations()) == 11
    await client.aclose()
    repository.close()
    compliance.close()
