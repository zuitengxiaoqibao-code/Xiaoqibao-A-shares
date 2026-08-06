from datetime import datetime, timezone
from decimal import Decimal

import pytest

from qibao_api.gongbu.tdx_local_professional import (
    TdxProfessionalDataUnavailable,
    TdxLocalProfessionalSource,
    TdxQuantPythonSource,
    inspect_tdx_quant_python_roots,
    parse_tdx_professional_rows,
    validate_tdx_professional_fields,
)


NOW = datetime(2026, 8, 7, 8, 0, tzinfo=timezone.utc)


def test_professional_fields_use_official_table_prefixes_only() -> None:
    assert validate_tdx_professional_fields("get_financial_data", ("Fn193", "Fn194")) == ("Fn193", "Fn194")
    assert validate_tdx_professional_fields("get_gpjy_value", ("GP1", "GP5")) == ("GP1", "GP5")
    assert validate_tdx_professional_fields("get_bkjy_value", ("BK5",)) == ("BK5",)
    assert validate_tdx_professional_fields("get_scjy_value", ("SC1",)) == ("SC1",)
    assert validate_tdx_professional_fields("get_gp_one_data", ("GO1", "GO47")) == ("GO1", "GO47")

    with pytest.raises(ValueError):
        validate_tdx_professional_fields("get_financial_data", ("PE",))
    with pytest.raises(ValueError):
        validate_tdx_professional_fields("get_gpjy_value", ("Fn193",))


def test_parse_professional_rows_preserves_explicit_values_and_missing_fields() -> None:
    result = parse_tdx_professional_rows(
        {
            "ErrorId": "0",
            "Value": [
                {"Code": "600000.SH", "Fn193": "12.5", "Fn194": "--", "Fn195": "0"},
            ],
        },
        method="get_financial_data",
        fetched_at=NOW,
    )

    assert len(result) == 1
    assert result[0].symbol == "600000"
    assert result[0].values == {"Fn193": Decimal("12.5"), "Fn195": Decimal("0")}
    assert result[0].source == "tdx-local-rpc-professional"


def test_professional_source_sends_table_list_and_never_field_list() -> None:
    class Rpc:
        def __init__(self) -> None:
            self.calls = []

        def available(self) -> bool:
            return True

        def call(self, method, params):
            self.calls.append((method, params))
            return {"ErrorId": "0", "Value": [{"Code": "600000.SH", "Fn193": "12.5"}]}

        def close(self) -> None:
            return None

    rpc = Rpc()
    source = TdxLocalProfessionalSource(lambda: rpc, clock=lambda: NOW)
    result = source.fetch(
        method="get_financial_data",
        stock_codes=("600000.SH",),
        fields=("Fn193",),
        start_time="20260101",
        end_time="20260807",
    )

    assert result[0].values["Fn193"] == Decimal("12.5")
    assert rpc.calls == [
        (
            "get_financial_data",
            {
                "stock_list": ["600000.SH"],
                "table_list": ["Fn193"],
                "start_time": "20260101000000",
                "end_time": "20260807000000",
                "report_type": "report_time",
            },
        )
    ]


def test_professional_source_reports_unavailable_without_bridge() -> None:
    class MissingRpc:
        def available(self) -> bool:
            return False

        def close(self) -> None:
            return None

    source = TdxLocalProfessionalSource(lambda: MissingRpc(), clock=lambda: NOW)
    with pytest.raises(TdxProfessionalDataUnavailable, match="bridge unavailable"):
        source.fetch(
            method="get_financial_data",
            stock_codes=("600000.SH",),
            fields=("Fn193",),
        )


def test_python_professional_source_calls_only_read_only_tq_method() -> None:
    class FakeTq:
        def __init__(self) -> None:
            self.calls = []

        def initialize(self, path):
            self.calls.append(("initialize", path))

        def get_financial_data(self, **kwargs):
            self.calls.append(("get_financial_data", kwargs))
            return {"600000.SH": [{"Fn193": "12.5"}]}

        def close(self):
            self.calls.append(("close",))

    class FakeModule:
        def __init__(self) -> None:
            self.tq = FakeTq()

    module = FakeModule()
    source = TdxQuantPythonSource(
        ("D:/new_tdx64",),
        module_loader=lambda _path: module,
        clock=lambda: NOW,
    )
    result = source.fetch(
        method="get_financial_data",
        stock_codes=("600000.SH",),
        fields=("Fn193",),
    )

    assert result[0].source == "tdx-python-professional"
    assert result[0].symbol == "600000"
    assert result[0].values["Fn193"] == Decimal("12.5")
    assert module.tq.calls[1][0] == "get_financial_data"
    assert module.tq.calls[1][1]["field_list"] == ["Fn193"]
    assert module.tq.calls[-1] == ("close",)


def test_python_professional_source_reuses_loaded_module_between_reads() -> None:
    class FakeTq:
        def __init__(self) -> None:
            self.calls = []

        def initialize(self, path):
            self.calls.append(("initialize", path))

        def get_financial_data(self, **kwargs):
            self.calls.append(("get_financial_data", kwargs))
            return {"600000.SH": [{"Fn193": "12.5"}]}

        def close(self):
            self.calls.append(("close",))

    class FakeModule:
        def __init__(self) -> None:
            self.tq = FakeTq()

    module = FakeModule()
    load_count = 0

    def load(_path):
        nonlocal load_count
        load_count += 1
        return module

    source = TdxQuantPythonSource(
        ("D:/new_tdx64",), module_loader=load, clock=lambda: NOW
    )
    for _ in range(2):
        source.fetch(
            method="get_financial_data",
            stock_codes=("600000.SH",),
            fields=("Fn193",),
        )

    assert load_count == 1
    assert [call[0] for call in module.tq.calls].count("initialize") == 2


def test_rpc_professional_source_falls_back_to_lazy_python_source() -> None:
    class MissingRpc:
        def available(self) -> bool:
            return False

        def close(self) -> None:
            return None

    class Fallback:
        def fetch(self, **_kwargs):
            return parse_tdx_professional_rows(
                {"ErrorId": "0", "Value": [{"Code": "600000.SH", "Fn193": "12.5"}]},
                method="get_financial_data",
                fetched_at=NOW,
                source="tdx-python-professional",
            )

    source = TdxLocalProfessionalSource(
        lambda: MissingRpc(),
        fallback=Fallback(),
        clock=lambda: NOW,
    )
    result = source.fetch(
        method="get_financial_data",
        stock_codes=("600000.SH",),
        fields=("Fn193",),
    )

    assert result[0].source == "tdx-python-professional"


def test_rpc_professional_source_falls_back_when_bridge_method_fails() -> None:
    class Rpc:
        def __init__(self) -> None:
            self.closed = 0

        def available(self) -> bool:
            return True

        def call(self, _method, _params):
            raise OSError("unsupported method")

        def close(self) -> None:
            self.closed += 1

    class Fallback:
        def fetch(self, **_kwargs):
            return parse_tdx_professional_rows(
                {"ErrorId": "0", "Value": [{"Code": "600000.SH", "Fn193": "12.5"}]},
                method="get_financial_data",
                fetched_at=NOW,
                source="tdx-python-professional",
            )

    rpc = Rpc()
    result = TdxLocalProfessionalSource(
        lambda: rpc,
        fallback=Fallback(),
        clock=lambda: NOW,
    ).fetch(
        method="get_financial_data",
        stock_codes=("600000.SH",),
        fields=("Fn193",),
    )

    assert result[0].source == "tdx-python-professional"
    assert rpc.closed >= 1


def test_inspect_python_professional_root_reports_detected_only_without_importing(
    tmp_path,
) -> None:
    module = tmp_path / "PYPlugins" / "user" / "tqcenter.py"
    module.parent.mkdir(parents=True)
    module.write_text("# vendor module placeholder", encoding="utf-8")
    (tmp_path / "PYPlugins" / "TPythClient.dll").write_bytes(b"dll")

    result = inspect_tdx_quant_python_roots((tmp_path,))

    assert result.status == "detected_only"
    assert result.module_path == str(module)
