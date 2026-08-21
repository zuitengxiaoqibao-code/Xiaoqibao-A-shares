import json
import sqlite3
import zipfile

import duckdb

from qibao_api.data_sources.file_adapter import FileImportService


def test_inspect_and_ingest_gbk_csv_normalizes_symbol_and_quarantines_bad_rows(tmp_path) -> None:
    source = tmp_path / "quotes.csv"
    source.write_bytes("股票代码,日期,收盘价\n600519,2026-08-20,1500\nBAD,not-a-date,\n".encode("gbk"))
    service = FileImportService(tmp_path / "imports")

    preview = service.inspect(source)
    assert preview.format == "csv"
    assert preview.row_count == 2
    assert "股票代码" in preview.columns

    result = service.ingest(source, {"股票代码": "symbol", "日期": "as_of", "收盘价": "close"})
    assert result.batch.records[0]["symbol"] == "600519"
    assert result.batch.quality_status == "partial"
    assert result.quarantined_rows == 1
    assert result.quarantine_reasons[0].startswith("第 ")


def test_inspect_supports_json_parquet_sqlite_and_zip(tmp_path) -> None:
    rows = [{"symbol": "600519", "as_of": "2026-08-20", "close": 1500.0}]
    json_path = tmp_path / "rows.json"
    json_path.write_text(json.dumps(rows), encoding="utf-8")
    parquet_path = tmp_path / "rows.parquet"
    with duckdb.connect() as connection:
        connection.execute(
            "COPY (SELECT '600519' AS symbol, '2026-08-20' AS as_of, 1500.0 AS close) "
            f"TO '{parquet_path.as_posix()}' (FORMAT PARQUET)"
        )
    sqlite_path = tmp_path / "rows.sqlite"
    with sqlite3.connect(sqlite_path) as connection:
        connection.execute("create table quotes(symbol text, as_of text, close real)")
        connection.execute("insert into quotes values ('600519', '2026-08-20', 1500.0)")
        connection.commit()
    zip_path = tmp_path / "rows.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.write(json_path, "nested/rows.json")

    service = FileImportService(tmp_path / "imports")
    assert service.inspect(json_path).format == "json"
    assert service.inspect(parquet_path).format == "parquet"
    assert service.inspect(sqlite_path).format == "sqlite"
    assert service.inspect(zip_path).format == "zip"
