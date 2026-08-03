import pandas as pd
import pytest

from qibao_api.gongbu import tdx_client
from qibao_api.gongbu.tdx_client import (
    TdxNodePool,
    create_tdx_client,
    select_tdx_server,
)


class FakeClient:
    def __init__(self, *, bars=None, finance=None, f10=None, close_error=None) -> None:
        self.bars_result = bars
        self.finance_result = finance
        self.f10_result = f10
        self.close_error = close_error
        self.close_calls = 0

    def bars(self, **kwargs):
        if isinstance(self.bars_result, Exception):
            raise self.bars_result
        return self.bars_result

    def finance(self, **kwargs):
        if isinstance(self.finance_result, Exception):
            raise self.finance_result
        return self.finance_result

    def F10(self, **kwargs):
        if isinstance(self.f10_result, Exception):
            raise self.f10_result
        return self.f10_result

    def close(self) -> None:
        self.close_calls += 1
        if self.close_error is not None:
            raise self.close_error


def test_select_tdx_server_skips_unreachable_nodes() -> None:
    servers = [("first", 7709), ("second", 7709)]

    selected = select_tdx_server(servers, probe=lambda host, port: host == "second")

    assert selected == ("second", 7709)


def test_default_factory_disables_nested_retry(monkeypatch) -> None:
    calls = []
    underlying = FakeClient(finance={"updated_date": 20260331})
    monkeypatch.setattr(
        tdx_client.Quotes,
        "factory",
        lambda **kwargs: calls.append(kwargs) or underlying,
    )
    client = create_tdx_client(
        servers=[("only", 7709)],
        probe=lambda host, port: True,
    )

    client.finance(symbol="600519")

    assert calls == [{
        "market": "std",
        "server": ("only", 7709),
        "timeout": 3,
        "auto_retry": False,
    }]


def test_f10_is_exposed_through_the_failover_client_and_retries_empty_result() -> None:
    servers = [("empty", 7709), ("ready", 7709)]
    clients = {
        servers[0]: FakeClient(f10=""),
        servers[1]: FakeClient(f10="公司概况原文"),
    }
    client = create_tdx_client(
        servers=servers,
        probe=lambda host, port: True,
        client_factory=lambda *, market, server: clients[server],
    )

    result = client.F10(symbol="600519", name="公司概况")

    assert result == "公司概况原文"
    assert [clients[server].close_calls for server in servers] == [1, 1]


def test_f10_retries_when_a_node_returns_a_different_section_mapping() -> None:
    servers = [("partial", 7709), ("complete", 7709)]
    clients = {
        servers[0]: FakeClient(f10={"最新提示": "公告摘要"}),
        servers[1]: FakeClient(f10={"公司概况": "主营业务原文"}),
    }
    client = create_tdx_client(
        servers=servers,
        probe=lambda host, port: True,
        client_factory=lambda *, market, server: clients[server],
    )

    result = client.F10(symbol="600519", name="公司概况")

    assert result == {"公司概况": "主营业务原文"}
    assert [clients[server].close_calls for server in servers] == [1, 1]


def test_bars_retries_empty_result_and_closes_every_created_client() -> None:
    servers = [("first", 7709), ("second", 7709)]
    clients = {
        ("first", 7709): FakeClient(bars=pd.DataFrame()),
        ("second", 7709): FakeClient(bars=pd.DataFrame([{"close": 10.5}])),
    }

    def factory(*, market, server):
        assert market == "std"
        return clients[server]

    client = create_tdx_client(
        servers=servers,
        probe=lambda host, port: True,
        client_factory=factory,
    )

    result = client.bars(symbol="600519", frequency=9, start=0, offset=20)

    assert result.equals(pd.DataFrame([{"close": 10.5}]))
    assert [clients[server].close_calls for server in servers] == [1, 1]


def test_successful_server_is_promoted_for_the_next_request() -> None:
    servers = [("empty", 7709), ("ready", 7709)]
    calls: list[str] = []

    def factory(*, market, server):
        calls.append(server[0])
        if server[0] == "empty":
            return FakeClient(bars=pd.DataFrame())
        return FakeClient(bars=pd.DataFrame([{"close": 10.5}]))

    pool = TdxNodePool(servers, cooldown_seconds=60)
    client = create_tdx_client(
        pool=pool,
        probe=lambda host, port: True,
        client_factory=factory,
    )

    client.bars(symbol="600519")
    client.bars(symbol="000001")

    assert calls == ["empty", "ready", "ready"]


def test_node_pool_retries_all_nodes_when_every_node_is_cooling_down() -> None:
    now = [100.0]
    servers = [("first", 7709), ("second", 7709)]
    pool = TdxNodePool(servers, clock=lambda: now[0], cooldown_seconds=60)

    pool.record_failure(servers[0])
    pool.record_failure(servers[1])

    assert pool.ordered_servers() == tuple(servers)


def test_finance_retries_exception_and_closes_every_created_client() -> None:
    servers = [("first", 7709), ("second", 7709)]
    clients = {
        ("first", 7709): FakeClient(finance=TimeoutError("timed out")),
        ("second", 7709): FakeClient(finance={"updated_date": 20260331}),
    }

    client = create_tdx_client(
        servers=servers,
        probe=lambda host, port: True,
        client_factory=lambda *, market, server: clients[server],
    )

    result = client.finance(symbol="600519")

    assert result == {"updated_date": 20260331}
    assert [clients[server].close_calls for server in servers] == [1, 1]


def test_operation_and_close_failures_still_retry_the_next_server() -> None:
    servers = [("first", 7709), ("second", 7709)]
    clients = {
        ("first", 7709): FakeClient(
            bars=TimeoutError("operation secret"),
            close_error=OSError("cleanup secret"),
        ),
        ("second", 7709): FakeClient(bars=[{"close": 10.5}]),
    }
    client = create_tdx_client(
        servers=servers,
        probe=lambda host, port: True,
        client_factory=lambda *, market, server: clients[server],
    )

    result = client.bars(symbol="600519")

    assert result == [{"close": 10.5}]
    assert [clients[server].close_calls for server in servers] == [1, 1]
    assert client.cleanup_errors == ("first:7709 (close failed: OSError)",)


def test_successful_response_survives_close_failure() -> None:
    underlying = FakeClient(
        finance={"updated_date": 20260331},
        close_error=OSError("cleanup secret"),
    )
    client = create_tdx_client(
        servers=[("only", 7709)],
        probe=lambda host, port: True,
        client_factory=lambda *, market, server: underlying,
    )

    result = client.finance(symbol="600519")

    assert result == {"updated_date": 20260331}
    assert underlying.close_calls == 1
    assert client.cleanup_errors == ("only:7709 (close failed: OSError)",)


def test_all_failed_error_lists_each_server_reason_and_skips_unreachable_client() -> None:
    servers = [
        ("unreachable", 7709),
        ("create-error", 7709),
        ("operation-error", 7709),
        ("empty", 7709),
    ]
    created_servers = []
    operation_error_client = FakeClient(
        bars=TimeoutError("operation secret"),
        close_error=OSError("cleanup secret"),
    )
    empty_client = FakeClient(bars=[])

    def factory(*, market, server):
        created_servers.append(server)
        if server[0] == "create-error":
            raise RuntimeError("credentials must not leak")
        if server[0] == "operation-error":
            return operation_error_client
        return empty_client

    client = create_tdx_client(
        servers=servers,
        probe=lambda host, port: host != "unreachable",
        client_factory=factory,
    )

    with pytest.raises(RuntimeError) as captured:
        client.bars(symbol="600519", frequency=9, start=0, offset=20)

    assert str(captured.value) == (
        "mootdx bars failed for all servers: unreachable:7709 (unreachable); "
        "create-error:7709 (client creation failed: RuntimeError); "
        "operation-error:7709 (bars failed: TimeoutError; close failed: OSError); "
        "empty:7709 (empty response)"
    )
    assert created_servers == [
        ("create-error", 7709),
        ("operation-error", 7709),
        ("empty", 7709),
    ]
    assert operation_error_client.close_calls == 1
    assert empty_client.close_calls == 1


def test_tdx_records_each_node_attempt_without_leaking_observer_failures() -> None:
    servers = [("first", 7709), ("second", 7709)]
    clients = {
        servers[0]: FakeClient(bars=pd.DataFrame()),
        servers[1]: FakeClient(bars=pd.DataFrame([{"close": 10.5}])),
    }
    events = []

    def observer(event) -> None:
        events.append(event)
        raise RuntimeError("telemetry must not break data")

    client = create_tdx_client(
        servers=servers,
        probe=lambda host, port: True,
        client_factory=lambda *, market, server: clients[server],
        observer=observer,
    )

    result = client.bars(symbol="600519", frequency=9, start=0, offset=20)

    assert result.equals(pd.DataFrame([{"close": 10.5}]))
    assert [(item.source, item.operation, item.target, item.status) for item in events] == [
        ("mootdx", "bars", "first:7709", "empty"),
        ("mootdx", "bars", "second:7709", "ready"),
    ]
    assert all(item.latency_ms >= 0 for item in events)
