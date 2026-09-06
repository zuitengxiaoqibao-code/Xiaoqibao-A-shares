from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest

from qibao_api.a_shares.models import (
    CandidateBoard,
    CandidateEntry,
    CandidateExclusion,
    FactorSnapshot,
)
from qibao_api.contracts.decision import EvidenceReference
from qibao_api.contracts.industry import ShenwanIndustry
from qibao_api.gongbu.market_feed import MarketFeedSnapshot
from qibao_api.shangshu.decision_runtime import (
    DecisionSymbolSource,
    DeterministicIntradayEvaluator,
    RepositoryCandidateFactorSource,
    RepositoryEvidenceSource,
    RepositoryRiskSource,
    TencentPollingMarketFeed,
)
from qibao_api.shangshu.intraday_monitor import IntradayEvaluationContext
from qibao_api.zhongshu.premarket_decision import (
    CandidateInputSnapshot,
    ComplianceInputSnapshot,
    MarketRiskInputSnapshot,
)


NOW = datetime(2026, 7, 15, 9, 20, tzinfo=timezone.utc)


class Compliance:
    def __init__(self):
        self.calls = []

    def require_feature_sources(self, feature, asset):
        self.calls.append((feature, asset))


def tencent_quote_line(symbol: str, *, price: str = "10.25") -> bytes:
    fields = [""] * 50
    fields[1] = "浦发银行" if symbol == "600000" else "平安银行"
    fields[2] = symbol
    fields[3] = price
    fields[4] = "10.10"
    fields[6] = "1000"
    fields[30] = "20260715103000"
    prefix = "sh" if symbol.startswith("6") else "sz"
    return f'v_{prefix}{symbol}="{"~".join(fields)}";'.encode("gbk")


def test_polling_feed_fetches_multiple_symbols_in_one_tencent_request():
    requested_urls = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        return httpx.Response(
            200,
            content=tencent_quote_line("000001") + b"\n" + tencent_quote_line("600000"),
        )

    compliance = Compliance()
    cutoff = datetime(2026, 7, 15, 10, 31, tzinfo=timezone(timedelta(hours=8)))
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        snapshots = TencentPollingMarketFeed(client, compliance).snapshot_many(
            ("600000", "000001"), cutoff=cutoff,
        )

    assert requested_urls == ["https://qt.gtimg.cn/q=sh600000,sz000001"]
    assert [item.symbol for item in snapshots] == ["600000", "000001"]
    assert compliance.calls == [("realtime_quotes", "a_share")]


def test_polling_feed_retries_only_a_symbol_missing_from_the_batch():
    requested_urls = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        if len(requested_urls) == 1:
            return httpx.Response(200, content=tencent_quote_line("600000"))
        return httpx.Response(200, content=tencent_quote_line("000001"))

    cutoff = datetime(2026, 7, 15, 10, 31, tzinfo=timezone(timedelta(hours=8)))
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        snapshots = TencentPollingMarketFeed(client, Compliance()).snapshot_many(
            ("600000", "000001"), cutoff=cutoff,
        )

    assert requested_urls == [
        "https://qt.gtimg.cn/q=sh600000,sz000001",
        "https://qt.gtimg.cn/q=sz000001",
    ]
    assert [item.symbol for item in snapshots] == ["600000", "000001"]


def test_polling_feed_retries_the_whole_batch_after_a_transport_failure():
    requested_urls = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        if len(requested_urls) == 1:
            raise httpx.ReadTimeout("upstream timeout", request=request)
        return httpx.Response(
            200,
            content=tencent_quote_line("600000") + b"\n" + tencent_quote_line("000001"),
        )

    cutoff = datetime(2026, 7, 15, 10, 31, tzinfo=timezone(timedelta(hours=8)))
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        snapshots = TencentPollingMarketFeed(client, Compliance()).snapshot_many(
            ("600000", "000001"), cutoff=cutoff,
        )

    assert requested_urls == [
        "https://qt.gtimg.cn/q=sh600000,sz000001",
        "https://qt.gtimg.cn/q=sh600000,sz000001",
    ]
    assert [item.symbol for item in snapshots] == ["600000", "000001"]


def test_polling_feed_rejects_a_batch_that_is_still_incomplete_after_retry():
    requested_urls = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        return httpx.Response(200, content=tencent_quote_line("600000"))

    cutoff = datetime(2026, 7, 15, 10, 31, tzinfo=timezone(timedelta(hours=8)))
    def fallback_client_factory():
        return httpx.Client(transport=httpx.MockTransport(handler))

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ValueError, match="incomplete Tencent quote batch.*000001"):
            TencentPollingMarketFeed(
                client,
                Compliance(),
                fallback_client_factory=fallback_client_factory,
            ).snapshot_many(
                ("600000", "000001"), cutoff=cutoff,
            )

    assert requested_urls == [
        "https://qt.gtimg.cn/q=sh600000,sz000001",
        "https://qt.gtimg.cn/q=sz000001",
        "https://qt.gtimg.cn/q=sz000001",
    ]


def test_polling_feed_uses_a_direct_client_when_environment_network_is_incomplete():
    primary_urls = []
    direct_urls = []

    def primary_handler(request: httpx.Request) -> httpx.Response:
        primary_urls.append(str(request.url))
        return httpx.Response(200, content=b"")

    def direct_handler(request: httpx.Request) -> httpx.Response:
        direct_urls.append(str(request.url))
        return httpx.Response(200, content=tencent_quote_line("600000"))

    def fallback_client_factory():
        return httpx.Client(transport=httpx.MockTransport(direct_handler))

    cutoff = datetime(2026, 7, 15, 10, 31, tzinfo=timezone(timedelta(hours=8)))
    with httpx.Client(transport=httpx.MockTransport(primary_handler)) as client:
        snapshots = TencentPollingMarketFeed(
            client,
            Compliance(),
            fallback_client_factory=fallback_client_factory,
        ).snapshot_many(("600000",), cutoff=cutoff)

    assert primary_urls == [
        "https://qt.gtimg.cn/q=sh600000",
        "https://qt.gtimg.cn/q=sh600000",
    ]
    assert direct_urls == ["https://qt.gtimg.cn/q=sh600000"]
    assert [item.symbol for item in snapshots] == ["600000"]


class Candidates:
    def __init__(self, board):
        self.board = board
        self.cutoffs = []

    def candidates(self, _date, *, cutoff=None):
        self.cutoffs.append(cutoff)
        return self.board


class Audit:
    def __init__(self, findings=()):
        self.findings = findings

    def list_findings(self, *, asset):
        return list(self.findings)


def board(scores):
    entries = [SimpleNamespace(score=score) for score in scores]
    return SimpleNamespace(
        universe_status="ready" if entries else "empty", short_term=entries,
        swing=[], snapshot_id="candidate-1", model_dump=lambda mode: {"scores": scores},
    )


def test_market_risk_is_available_from_candidate_breadth_without_audit_findings():
    candidates = Candidates(board([12, 8]))
    result = RepositoryRiskSource(Audit(), candidates).summarize(
        date(2026, 7, 15), NOW
    )

    assert result.available is True
    assert result.market_state == "strong"
    assert result.risks == ()
    assert candidates.cutoffs == [NOW]


def test_audit_findings_are_an_additional_market_risk_signal():
    finding = SimpleNamespace(
        detected_at=NOW, resolution_state="open", severity="critical",
        finding_type="data_drift", model_dump=lambda mode: {"finding_id": "f1"},
    )
    result = RepositoryRiskSource(Audit((finding,)), Candidates(board([12]))).summarize(
        date(2026, 7, 15), NOW
    )

    assert result.available is True
    assert result.market_state == "weak"
    assert result.risks == ("data_drift",)


def test_market_risk_degrades_when_candidate_factor_data_is_unavailable():
    result = RepositoryRiskSource(Audit(), Candidates(board([]))).summarize(
        date(2026, 7, 15), NOW
    )

    assert result.available is False
    assert result.market_state == "insufficient_data"
    assert "market_factor_evidence_unavailable" in result.risks


def test_market_risk_includes_verified_topics_industries_and_candidate_fund_flow():
    candidate_board = SimpleNamespace(
        universe_status="ready",
        short_term=[SimpleNamespace(symbol="600000", score=12)],
        swing=[SimpleNamespace(symbol="600519", score=8)],
        snapshot_id="candidate-1",
        model_dump=lambda mode: {"symbols": ["600000", "600519"]},
    )
    candidates = Candidates(candidate_board)
    news = SimpleNamespace(effective_events=lambda cutoff=None: [
        SimpleNamespace(
            review_state="verified", themes=("人工智能",), industries=("软件服务",),
            occurred_at=NOW, normalized_at=NOW,
        ),
        SimpleNamespace(
            review_state="verified", themes=("旧热点",), industries=("旧行业",),
            occurred_at=NOW - timedelta(days=2), normalized_at=NOW - timedelta(days=2),
        ),
    ])
    classifications = SimpleNamespace(latest=lambda symbol, as_of, cutoff=None: SimpleNamespace(
        industry="供应商原始分类",
        shenwan_industry=ShenwanIndustry(
            code="SW801780" if symbol == "600000" else "SW801120",
            name="银行" if symbol == "600000" else "食品饮料",
            level="一级",
            version="SW2021",
        ),
    ))
    flows = SimpleNamespace(latest=lambda symbol, as_of, cutoff=None: SimpleNamespace(
        flow_direction="inflow" if symbol == "600000" else "outflow",
    ))

    result = RepositoryRiskSource(
        Audit(), candidates, news_repository=news,
        classification_repository=classifications, fund_flow_repository=flows,
    ).summarize(date(2026, 7, 15), NOW)

    assert result.hot_topics == ("人工智能",)
    assert result.industries == ("软件服务", "银行", "食品饮料")
    assert (result.fund_flow_inflow_count, result.fund_flow_outflow_count) == (1, 1)
    assert result.fund_flow_available_count == 2


def test_market_risk_separates_pending_labels_from_verified_evidence():
    candidate_board = SimpleNamespace(
        universe_status="ready",
        short_term=[SimpleNamespace(symbol="600000", score=12)],
        swing=[],
        snapshot_id="candidate-1",
        model_dump=lambda mode: {"symbols": ["600000"]},
    )
    news = SimpleNamespace(effective_events=lambda cutoff=None: [
        SimpleNamespace(
            review_state="verified", themes=("已核验主题",), industries=("已核验行业",),
            occurred_at=NOW, normalized_at=NOW,
        ),
        SimpleNamespace(
            review_state="pending", themes=("待核验主题",), industries=("待核验行业",),
            occurred_at=NOW, normalized_at=NOW,
        ),
        SimpleNamespace(
            review_state="pending", themes=(), industries=(),
            occurred_at=NOW, normalized_at=NOW,
        ),
        SimpleNamespace(
            review_state="rejected", themes=("拒绝主题",), industries=("拒绝行业",),
            occurred_at=NOW, normalized_at=NOW,
        ),
    ])

    result = RepositoryRiskSource(
        Audit(), Candidates(candidate_board), news_repository=news,
    ).summarize(date(2026, 7, 15), NOW)

    assert result.hot_topics == ("已核验主题",)
    assert result.industries == ("已核验行业",)
    assert result.pending_hot_topics == ("待核验主题",)
    assert result.pending_industries == ("待核验行业",)
    assert result.risks == ()


def test_market_risk_deduplicates_fund_flow_for_short_and_swing_membership():
    candidate_board = SimpleNamespace(
        universe_status="ready",
        short_term=[SimpleNamespace(symbol="600000", score=12)],
        swing=[SimpleNamespace(symbol="600000", score=8)],
        snapshot_id="candidate-1",
        model_dump=lambda mode: {"symbols": ["600000"]},
    )
    flows = SimpleNamespace(latest=lambda symbol, as_of, cutoff=None: SimpleNamespace(
        flow_direction="outflow",
    ))

    result = RepositoryRiskSource(
        Audit(), Candidates(candidate_board), fund_flow_repository=flows,
    ).summarize(date(2026, 7, 15), NOW)

    assert result.fund_flow_available_count == 1
    assert result.fund_flow_outflow_count == 1


def candidate_input(symbol: str = "600000") -> CandidateInputSnapshot:
    factor = FactorSnapshot(
        symbol=symbol, as_of=date(2026, 7, 15), close="9.16",
        return_5d="0.03", return_20d="-0.03", distance_ma20="0.02",
        volume_ratio_5_20="0.96", volatility_20d="0.01", drawdown_60d="-0.08",
        liquidity_amount_20d="600000000", source="baidu",
    )
    entry = CandidateEntry(
        symbol=symbol, horizon="short_term", score="40",
        score_breakdown={"trend": Decimal("10")}, factor_snapshot=factor,
    )
    return CandidateInputSnapshot(
        board=CandidateBoard(
            snapshot_id="candidate-live", as_of=date(2026, 7, 15),
            short_term=[entry], swing=[],
        ),
        captured_at=datetime(2026, 7, 15, 13, 0, tzinfo=timezone(timedelta(hours=8))),
        history_available=True,
    )


def test_symbol_source_uses_current_candidates_when_decision_pool_is_empty():
    repository = SimpleNamespace(cycles=lambda *_args: [])
    source = SimpleNamespace(candidates=lambda _date: candidate_input())

    symbols = DecisionSymbolSource(repository, source)(
        datetime(2026, 7, 15, 13, 0, tzinfo=timezone(timedelta(hours=8)))
    )

    assert symbols == ("600000",)


def test_symbol_source_merges_existing_cycles_with_current_candidates():
    advice = SimpleNamespace(symbol="600000")
    cycle = SimpleNamespace(advice=(advice,))
    repository = SimpleNamespace(cycles=lambda *_args: [cycle])
    source = SimpleNamespace(candidates=lambda _date: candidate_input("600519"))

    symbols = DecisionSymbolSource(repository, source)(
        datetime(2026, 7, 15, 13, 0, tzinfo=timezone(timedelta(hours=8)))
    )

    assert symbols == ("600000", "600519")


def test_candidate_factor_source_marks_a_computed_empty_board_as_available():
    empty = CandidateBoard(
        snapshot_id="candidate-empty", as_of=date(2026, 7, 15),
        short_term=[], swing=[],
        exclusions=[CandidateExclusion(
            symbol="600000", reason_code="insufficient_liquidity",
        )],
    )

    result = RepositoryCandidateFactorSource(Candidates(empty)).candidates(
        date(2026, 7, 15)
    )

    assert result.board.universe_status == "empty"
    assert result.history_available is True


def test_repository_evidence_source_uses_effective_events():
    raw = SimpleNamespace(
        event_id="raw",
        review_state="verified",
        occurred_at=NOW,
        normalized_at=NOW,
    )
    effective = SimpleNamespace(
        event_id="effective",
        review_state="verified",
        occurred_at=NOW,
        normalized_at=NOW,
    )
    repository = SimpleNamespace(
        events=lambda: [raw], effective_events=lambda cutoff=None: [effective]
    )

    result = RepositoryEvidenceSource(repository).snapshot(now=NOW, cutoff=NOW)

    assert [item.event_id for item in result] == ["effective"]


def test_intraday_evaluator_seeds_observation_when_premarket_advice_is_empty():
    local_now = datetime(2026, 7, 15, 13, 0, tzinfo=timezone(timedelta(hours=8)))
    candidates = candidate_input()
    quote = MarketFeedSnapshot(
        symbol="600000", price="9.20", change="0.04", change_percent="0.44",
        volume="1000", source="tencent", observed_at=local_now,
        fetched_at=local_now.astimezone(timezone.utc), quality="ready",
        source_snapshot_id="quote-live",
    )
    risk = MarketRiskInputSnapshot(
        snapshot_id="risk-live", captured_at=local_now, available=True,
        market_state="range", version="risk-v1", summary="range", risks=(),
    )
    compliance = ComplianceInputSnapshot(
        snapshot_id="compliance-live", captured_at=local_now, available=True,
        allowed=True, version="compliance-v1", risks=(),
    )

    result = DeterministicIntradayEvaluator().evaluate(IntradayEvaluationContext(
        now=local_now, window_start=local_now.replace(hour=9, minute=25),
        window_end=local_now, quotes=(quote,), current_advice=(),
        candidate_factor_input=candidates, risk_input=risk,
        compliance_input=compliance, evidence_input=(),
    ))

    assert [item.symbol for item in result.advice] == ["600000"]
    assert result.advice[0].action == "observe"
    assert "premarket_snapshot_unavailable" in result.advice[0].risks
    assert result.quality_reasons == ()


@pytest.mark.parametrize(
    ("change_percent", "action", "conclusion"),
    [
        ("3.20", "observe", "盘中走强，等待放量确认"),
        ("-3.20", "wait", "盘中走弱，等待止跌确认"),
    ],
)
def test_intraday_evaluator_turns_live_quote_change_into_a_beginner_friendly_signal(
    change_percent, action, conclusion,
):
    local_now = datetime(2026, 7, 15, 13, 0, tzinfo=timezone(timedelta(hours=8)))
    candidates = candidate_input()
    quote = MarketFeedSnapshot(
        symbol="600000", price="9.20", change="0.04", change_percent=change_percent,
        volume="1000", source="tencent", observed_at=local_now,
        fetched_at=local_now.astimezone(timezone.utc), quality="ready",
        source_snapshot_id="quote-live",
    )
    risk = MarketRiskInputSnapshot(
        snapshot_id="risk-live", captured_at=local_now, available=True,
        market_state="range", version="risk-v1", summary="range", risks=(),
    )
    compliance = ComplianceInputSnapshot(
        snapshot_id="compliance-live", captured_at=local_now, available=True,
        allowed=True, version="compliance-v1", risks=(),
    )

    result = DeterministicIntradayEvaluator().evaluate(IntradayEvaluationContext(
        now=local_now, window_start=local_now.replace(hour=9, minute=25),
        window_end=local_now, quotes=(quote,), current_advice=(),
        candidate_factor_input=candidates, risk_input=risk,
        compliance_input=compliance, evidence_input=(),
    ))

    assert result.advice[0].action == action
    assert result.advice[0].conclusion == conclusion
    assert result.market_state in {"strong", "weak"}
    assert any("盘中行情" in item.summary for item in result.advice[0].supporting_evidence)


def test_intraday_evaluator_rounds_percent_only_in_human_facing_text():
    local_now = datetime(2026, 7, 15, 13, 0, tzinfo=timezone(timedelta(hours=8)))
    raw_change_percent = Decimal("-0.5305840395872882230994686217")
    quote = MarketFeedSnapshot(
        symbol="600000", price="9.20", change="-0.05", change_percent=raw_change_percent,
        volume="1000", source="tencent", observed_at=local_now,
        fetched_at=local_now.astimezone(timezone.utc), quality="ready",
        source_snapshot_id="quote-live",
    )
    risk = MarketRiskInputSnapshot(
        snapshot_id="risk-live", captured_at=local_now, available=True,
        market_state="range", version="risk-v1", summary="range", risks=(),
    )
    compliance = ComplianceInputSnapshot(
        snapshot_id="compliance-live", captured_at=local_now, available=True,
        allowed=True, version="compliance-v1", risks=(),
    )

    result = DeterministicIntradayEvaluator().evaluate(IntradayEvaluationContext(
        now=local_now, window_start=local_now.replace(hour=9, minute=25),
        window_end=local_now, quotes=(quote,), current_advice=(),
        candidate_factor_input=candidate_input(), risk_input=risk,
        compliance_input=compliance, evidence_input=(),
    ))

    advice = result.advice[0]
    assert "盘中涨跌 -0.53%" in advice.plain_language_explanation
    assert "涨跌 -0.53%" in advice.supporting_evidence[-1].summary
    assert advice.quantitative_result["change_percent"] == raw_change_percent


def test_intraday_evaluator_attaches_verified_news_as_supporting_or_contrary_evidence():
    local_now = datetime(2026, 7, 15, 13, 0, tzinfo=timezone(timedelta(hours=8)))
    quote = MarketFeedSnapshot(
        symbol="600000", price="9.20", change="0.04", change_percent="0.44",
        volume="1000", source="tencent", observed_at=local_now,
        fetched_at=local_now.astimezone(timezone.utc), quality="ready",
        source_snapshot_id="quote-live",
    )
    risk = MarketRiskInputSnapshot(
        snapshot_id="risk-live", captured_at=local_now, available=True,
        market_state="range", version="risk-v1", summary="range", risks=(),
    )
    compliance = ComplianceInputSnapshot(
        snapshot_id="compliance-live", captured_at=local_now, available=True,
        allowed=True, version="compliance-v1", risks=(),
    )
    event = SimpleNamespace(
        event_id="news-risk", affected_instruments=(("a_share", "600000"),),
        event_type="risk_notice", themes=("风险事件",), normalized_at=local_now,
        citations=(SimpleNamespace(publisher="交易所", canonical_url="https://example.com"),),
        headline="公司风险提示",
    )

    result = DeterministicIntradayEvaluator().evaluate(IntradayEvaluationContext(
        now=local_now, window_start=local_now.replace(hour=9, minute=25),
        window_end=local_now, quotes=(quote,), current_advice=(),
        candidate_factor_input=candidate_input(), risk_input=risk,
        compliance_input=compliance, evidence_input=(event,),
    ))

    advice = result.advice[0]
    assert [item.evidence_id for item in advice.contrary_evidence] == ["news-news-risk"]
    assert "风险新闻" in advice.risks
    assert result.news_event_ids == ("news-risk",)


def test_intraday_evaluator_references_only_unique_related_news_inside_window():
    local_now = datetime(2026, 7, 15, 13, 0, tzinfo=timezone(timedelta(hours=8)))
    window_start = local_now.replace(hour=9, minute=25)
    quote = MarketFeedSnapshot(
        symbol="600000", price="9.20", change="0.04", change_percent="0.44",
        volume="1000", source="tencent", observed_at=local_now,
        fetched_at=local_now.astimezone(timezone.utc), quality="ready",
        source_snapshot_id="quote-live",
    )
    risk = MarketRiskInputSnapshot(
        snapshot_id="risk-live", captured_at=local_now, available=True,
        market_state="range", version="risk-v1", summary="range", risks=(),
    )
    compliance = ComplianceInputSnapshot(
        snapshot_id="compliance-live", captured_at=local_now, available=True,
        allowed=True, version="compliance-v1", risks=(),
    )

    def event(event_id, symbol, normalized_at):
        return SimpleNamespace(
            event_id=event_id, affected_instruments=(("a_share", symbol),),
            event_type="company_update", themes=(), normalized_at=normalized_at,
            citations=(), headline=event_id,
        )

    related_b = event("news-b", "600000", local_now)
    related_a = event("news-a", "600000", local_now - timedelta(minutes=1))
    unrelated = event("news-unrelated", "000001", local_now)
    too_old = event("news-old", "600000", window_start - timedelta(seconds=1))
    result = DeterministicIntradayEvaluator().evaluate(IntradayEvaluationContext(
        now=local_now, window_start=window_start, window_end=local_now,
        quotes=(quote,), current_advice=(), candidate_factor_input=candidate_input(),
        risk_input=risk, compliance_input=compliance,
        evidence_input=(related_b, unrelated, related_a, related_b, too_old),
    ))

    assert result.news_event_ids == ("news-a", "news-b")


def test_intraday_evaluator_replaces_prior_live_quotes_and_preserves_baseline_evidence():
    local_now = datetime(2026, 7, 15, 13, 0, tzinfo=timezone(timedelta(hours=8)))
    window_start = local_now.replace(hour=9, minute=25)
    quote = MarketFeedSnapshot(
        symbol="600000", price="9.20", change="0.04", change_percent="0.44",
        volume="1000", source="tencent", observed_at=local_now,
        fetched_at=local_now.astimezone(timezone.utc), quality="ready",
        source_snapshot_id="quote-current",
    )
    risk = MarketRiskInputSnapshot(
        snapshot_id="risk-live", captured_at=local_now, available=True,
        market_state="range", version="risk-v1", summary="range", risks=(),
    )
    compliance = ComplianceInputSnapshot(
        snapshot_id="compliance-live", captured_at=local_now, available=True,
        allowed=True, version="compliance-v1", risks=(),
    )
    baseline_factor = EvidenceReference(
        evidence_id="factor-current", evidence_kind="candidate_factor",
        source="baidu", snapshot_id="candidate-live", summary="候选因子",
        observed_at=window_start - timedelta(minutes=5),
    )
    baseline_news = EvidenceReference(
        evidence_id="news-baseline", evidence_kind="verified_news",
        source="交易所", snapshot_id="event-baseline", summary="已核验事件",
        observed_at=window_start - timedelta(minutes=3),
    )
    typed_old_quote = EvidenceReference(
        evidence_id="provider-old", evidence_kind="live_quote",
        source="provider", snapshot_id="provider-old", summary="旧盘中行情",
        observed_at=local_now - timedelta(minutes=2),
    )
    legacy_old_quote = EvidenceReference(
        evidence_id="tencent-legacy", source="tencent",
        snapshot_id="tencent-legacy", summary="旧格式盘中行情",
        observed_at=local_now - timedelta(minutes=1),
    )
    current = DeterministicIntradayEvaluator()._seed_advice(
        SimpleNamespace(
            candidate_factor_input=candidate_input(), now=local_now,
            risk_input=risk, compliance_input=compliance,
        ),
        {"600000": quote},
    )[0].model_copy(update={
        "supporting_evidence": (
            baseline_factor, baseline_news, typed_old_quote, legacy_old_quote,
        ),
    })

    result = DeterministicIntradayEvaluator().evaluate(IntradayEvaluationContext(
        now=local_now, window_start=window_start, window_end=local_now,
        quotes=(quote,), current_advice=(current,),
        candidate_factor_input=candidate_input(), risk_input=risk,
        compliance_input=compliance, evidence_input=(),
    ))

    evidence = result.advice[0].supporting_evidence
    assert [item.evidence_id for item in evidence] == [
        "factor-current", "news-baseline", "quote-current",
    ]
    assert evidence[-1].evidence_kind == "live_quote"


@pytest.mark.parametrize(
    ("failure", "expected_reason"),
    [
        ("no_quotes", "live_quotes_unavailable"),
        ("quote_quality", "live_quote_quality_blocked"),
        ("future_quote", "live_quote_timestamp_invalid"),
        ("stale_quote", "live_quotes_stale"),
        ("risk_unavailable", "risk_unavailable"),
        ("compliance_unavailable", "compliance_unavailable"),
        ("compliance_denied", "compliance_not_allowed"),
    ],
)
def test_intraday_evaluator_records_exact_reason_when_live_gate_is_not_valid(
    failure, expected_reason,
):
    local_now = datetime(2026, 7, 15, 13, 0, tzinfo=timezone(timedelta(hours=8)))
    observed_at = {
        "future_quote": local_now + timedelta(seconds=1),
        "stale_quote": local_now - timedelta(minutes=4),
    }.get(failure, local_now)
    quote = MarketFeedSnapshot(
        symbol="600000", price="9.20", change="0.04", change_percent="0.44",
        volume="1000", source="tencent", observed_at=observed_at,
        fetched_at=max(local_now, observed_at).astimezone(timezone.utc),
        quality="blocked" if failure == "quote_quality" else "ready",
        source_snapshot_id="quote-live",
    )
    risk = MarketRiskInputSnapshot(
        snapshot_id="risk-live", captured_at=local_now,
        available=failure != "risk_unavailable",
        market_state="range", version="risk-v1", summary="range", risks=(),
    )
    compliance = ComplianceInputSnapshot(
        snapshot_id="compliance-live", captured_at=local_now,
        available=failure != "compliance_unavailable",
        allowed=failure != "compliance_denied", version="compliance-v1", risks=(),
    )

    result = DeterministicIntradayEvaluator().evaluate(IntradayEvaluationContext(
        now=local_now, window_start=local_now.replace(hour=9, minute=25),
        window_end=local_now,
        quotes=() if failure == "no_quotes" else (quote,), current_advice=(),
        candidate_factor_input=candidate_input(), risk_input=risk,
        compliance_input=compliance, evidence_input=(),
    ))

    assert result.advice == ()
    assert result.status == "blocked"
    assert result.data_quality == "blocked"
    assert result.quality_reasons == (expected_reason,)


@pytest.mark.parametrize(
    ("now_time", "observed_time", "expected_status"),
    [
        ((11, 40, 0), (11, 30, 0), "ready"),
        ((11, 40, 0), (11, 26, 59), "blocked"),
        ((13, 0, 0), (11, 30, 0), "blocked"),
    ],
)
def test_intraday_evaluator_uses_last_fresh_morning_quote_only_during_lunch_break(
    now_time, observed_time, expected_status,
):
    china_tz = timezone(timedelta(hours=8))
    local_now = datetime(2026, 7, 15, *now_time, tzinfo=china_tz)
    observed_at = datetime(2026, 7, 15, *observed_time, tzinfo=china_tz)
    quote = MarketFeedSnapshot(
        symbol="600000", price="9.20", change="0.04", change_percent="0.44",
        volume="1000", source="tencent", observed_at=observed_at,
        fetched_at=local_now.astimezone(timezone.utc), quality="ready",
        source_snapshot_id="quote-lunch-break",
    )
    risk = MarketRiskInputSnapshot(
        snapshot_id="risk-live", captured_at=local_now, available=True,
        market_state="range", version="risk-v1", summary="range", risks=(),
    )
    compliance = ComplianceInputSnapshot(
        snapshot_id="compliance-live", captured_at=local_now, available=True,
        allowed=True, version="compliance-v1", risks=(),
    )

    result = DeterministicIntradayEvaluator().evaluate(IntradayEvaluationContext(
        now=local_now, window_start=local_now.replace(hour=9, minute=25),
        window_end=local_now, quotes=(quote,), current_advice=(),
        candidate_factor_input=candidate_input(), risk_input=risk,
        compliance_input=compliance, evidence_input=(),
    ))

    assert result.status == expected_status
    assert result.data_quality == expected_status


def test_intraday_evaluator_replaces_stale_advice_with_a_new_candidate():
    local_now = datetime(2026, 7, 15, 13, 0, tzinfo=timezone(timedelta(hours=8)))
    candidates = candidate_input("600519")
    quotes = tuple(
        MarketFeedSnapshot(
            symbol=symbol, price=price, change="0.04", change_percent="0.44",
            volume="1000", source="tencent", observed_at=local_now,
            fetched_at=local_now.astimezone(timezone.utc), quality="ready",
            source_snapshot_id=f"quote-{symbol}",
        )
        for symbol, price in (("600000", "9.20"), ("600519", "1400"))
    )
    risk = MarketRiskInputSnapshot(
        snapshot_id="risk-live", captured_at=local_now, available=True,
        market_state="range", version="risk-v1", summary="range", risks=(),
    )
    compliance = ComplianceInputSnapshot(
        snapshot_id="compliance-live", captured_at=local_now, available=True,
        allowed=True, version="compliance-v1", risks=(),
    )
    existing = DeterministicIntradayEvaluator()._seed_advice(
        SimpleNamespace(
            candidate_factor_input=candidate_input(), now=local_now,
            risk_input=risk, compliance_input=compliance,
        ),
        {"600000": quotes[0]},
    )

    result = DeterministicIntradayEvaluator().evaluate(IntradayEvaluationContext(
        now=local_now, window_start=local_now.replace(hour=9, minute=25),
        window_end=local_now, quotes=quotes, current_advice=existing,
        candidate_factor_input=candidates, risk_input=risk,
        compliance_input=compliance, evidence_input=(),
    ))

    assert {item.symbol for item in result.advice} == {"600519"}


def test_intraday_evaluator_blocks_current_result_when_risk_is_unavailable():
    local_now = datetime(2026, 7, 15, 13, 0, tzinfo=timezone(timedelta(hours=8)))
    available = candidate_input()
    unavailable = CandidateInputSnapshot(
        board=CandidateBoard(
            snapshot_id="candidate-unavailable", as_of=date(2026, 7, 15),
            universe_status="empty", short_term=[], swing=[],
        ),
        captured_at=local_now,
        history_available=False,
    )
    quote = MarketFeedSnapshot(
        symbol="600000", price="9.20", change="0.04", change_percent="0.44",
        volume="1000", source="tencent", observed_at=local_now,
        fetched_at=local_now.astimezone(timezone.utc), quality="ready",
        source_snapshot_id="quote-600000",
    )
    risk = MarketRiskInputSnapshot(
        snapshot_id="risk-live", captured_at=local_now, available=False,
        market_state="insufficient_data", version="risk-v1", summary="unavailable",
        risks=("market_factor_evidence_unavailable",),
    )
    compliance = ComplianceInputSnapshot(
        snapshot_id="compliance-live", captured_at=local_now, available=True,
        allowed=True, version="compliance-v1", risks=(),
    )
    existing = DeterministicIntradayEvaluator()._seed_advice(
        SimpleNamespace(
            candidate_factor_input=available, now=local_now,
            risk_input=risk, compliance_input=compliance,
        ),
        {"600000": quote},
    )

    result = DeterministicIntradayEvaluator().evaluate(IntradayEvaluationContext(
        now=local_now, window_start=local_now.replace(hour=9, minute=25),
        window_end=local_now, quotes=(quote,), current_advice=existing,
        candidate_factor_input=unavailable, risk_input=risk,
        compliance_input=compliance, evidence_input=(),
    ))

    assert result.advice == ()
    assert result.status == "blocked"
    assert result.quality_reasons == ("risk_unavailable",)


def test_intraday_evaluator_removes_existing_advice_after_a_computed_empty_board():
    local_now = datetime(2026, 7, 15, 13, 0, tzinfo=timezone(timedelta(hours=8)))
    available = candidate_input()
    computed_empty = RepositoryCandidateFactorSource(Candidates(CandidateBoard(
        snapshot_id="candidate-empty", as_of=date(2026, 7, 15),
        short_term=[], swing=[],
        exclusions=[CandidateExclusion(
            symbol="600000", reason_code="insufficient_liquidity",
        )],
    )), clock=lambda: local_now).candidates(date(2026, 7, 15))
    quote = MarketFeedSnapshot(
        symbol="600000", price="9.20", change="0.04", change_percent="0.44",
        volume="1000", source="tencent", observed_at=local_now,
        fetched_at=local_now.astimezone(timezone.utc), quality="ready",
        source_snapshot_id="quote-600000",
    )
    risk = MarketRiskInputSnapshot(
        snapshot_id="risk-live", captured_at=local_now, available=True,
        market_state="range", version="risk-v1", summary="range", risks=(),
    )
    compliance = ComplianceInputSnapshot(
        snapshot_id="compliance-live", captured_at=local_now, available=True,
        allowed=True, version="compliance-v1", risks=(),
    )
    existing = DeterministicIntradayEvaluator()._seed_advice(
        SimpleNamespace(
            candidate_factor_input=available, now=local_now,
            risk_input=risk, compliance_input=compliance,
        ),
        {"600000": quote},
    )

    result = DeterministicIntradayEvaluator().evaluate(IntradayEvaluationContext(
        now=local_now, window_start=local_now.replace(hour=9, minute=25),
        window_end=local_now, quotes=(quote,), current_advice=existing,
        candidate_factor_input=computed_empty, risk_input=risk,
        compliance_input=compliance, evidence_input=(),
    ))

    assert computed_empty.history_available is True
    assert result.advice == ()
