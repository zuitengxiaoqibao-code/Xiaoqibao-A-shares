from datetime import date

from qibao_api.a_shares.data_version import DataVersionStore


def test_data_version_store_publishes_and_reads_latest_point_in_time(tmp_path) -> None:
    store = DataVersionStore(tmp_path)
    first = store.publish(
        "daily",
        date(2026, 8, 20),
        ("tdx",),
        "a" * 64,
        "ready",
    )
    second = store.publish(
        "daily",
        date(2026, 8, 21),
        ("tdx", "tencent"),
        "b" * 64,
        "partial",
    )

    assert store.latest("daily", date(2026, 8, 20)).content_hash == first.content_hash
    assert store.latest("daily", date(2026, 8, 21)).content_hash == second.content_hash
    assert store.latest("daily", date(2026, 8, 19)) is None
