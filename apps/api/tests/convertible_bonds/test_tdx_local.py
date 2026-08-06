from datetime import datetime, timezone
from decimal import Decimal

import pytest

from qibao_api.convertible_bonds.adapters import ClauseDataUnavailable
from qibao_api.convertible_bonds.tdx_local import (
    FallbackClauseSource,
    TdxLocalClauseSource,
    parse_tdx_kzz_info,
)


NOW = datetime(2026, 8, 6, 9, 30, tzinfo=timezone.utc)


def payload():
    return {
        "ErrorId": "0",
        "Value": {
            "bond_code": "113000",
            "linked_stock_code": "600000.SH",
            "conversion_price": "8.80",
            "maturity": "2030-01-01",
            "conversion_start": "2026-02-01",
            "remaining_size": "1000000000",
            "redeem_clause": "满足条件后公告",
        },
    }


def test_parse_tdx_kzz_info_requires_explicit_contract_fields() -> None:
    snapshot = parse_tdx_kzz_info(payload(), bond_code="113000", fetched_at=NOW)

    assert snapshot.source == "tdx-local-rpc"
    assert snapshot.contract.linked_stock == "600000"
    assert snapshot.contract.conversion_price == Decimal("8.80")
    assert snapshot.contract.maturity.isoformat() == "2030-01-01"
    assert snapshot.strong_redemption.state == "announced"


def test_parse_tdx_kzz_info_rejects_partial_payload() -> None:
    with pytest.raises(ClauseDataUnavailable, match="fields are incomplete"):
        parse_tdx_kzz_info({"Value": {"conversion_price": "8.8"}}, bond_code="113000", fetched_at=NOW)


@pytest.mark.asyncio
async def test_tdx_local_clause_source_is_read_only_and_closes_rpc() -> None:
    class Rpc:
        def __init__(self):
            self.calls = []
            self.closed = False

        def available(self):
            return True

        def call(self, method, params):
            self.calls.append((method, params))
            return payload()

        def close(self):
            self.closed = True

    rpc = Rpc()
    snapshot = await TdxLocalClauseSource(lambda: rpc, clock=lambda: NOW).fetch("113000")

    assert snapshot.contract.bond_code == "113000"
    assert rpc.calls == [("get_kzz_info", {"stock_code": "113000.SH"})]
    assert rpc.closed is True


@pytest.mark.asyncio
async def test_fallback_clause_source_uses_eastmoney_when_local_is_unavailable() -> None:
    class Missing:
        async def fetch(self, bond_code):
            raise ClauseDataUnavailable("local unavailable")

    class Public:
        async def fetch(self, bond_code):
            return parse_tdx_kzz_info(payload(), bond_code=bond_code, fetched_at=NOW).model_copy(update={"source": "eastmoney"})

    result = await FallbackClauseSource(Missing(), Public()).fetch("113000")

    assert result.source == "eastmoney"
