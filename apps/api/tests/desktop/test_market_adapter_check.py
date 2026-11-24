import json

from qibao_desktop.market_adapter_check import check_market_adapters


def test_offline_native_check_does_not_create_user_data(tmp_path):
    output = tmp_path / "check.json"
    assert check_market_adapters(output) == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["eltdx"]["native_abi"] == 1
    assert report["axdata"]["adapter"] == "tencent"
    assert list(tmp_path.iterdir()) == [output]
