from __future__ import annotations

import tempfile
import zipfile
import shutil
import time
from collections.abc import Callable, Iterable
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from qibao_api.contracts.bars import DailyBar
from qibao_api.contracts.instruments import validate_a_share_code
from qibao_api.contracts.tdx_import import TdxImportError, TdxImportJob, TdxImportScan
from qibao_api.gongbu.tdx_local_daily import _a_share_symbol, read_tdx_day_bars


class TdxLocalDatabaseUnavailable(RuntimeError):
    """Raised when the local market database stays locked during an import."""

    def __init__(self, *, attempts: int, scanned_files: int, total_files: int | None) -> None:
        self.attempts = attempts
        self.scanned_files = scanned_files
        self.total_files = total_files
        super().__init__("本机日线扫描已完成，但本地行情数据库仍被其他任务占用")


class TdxLocalImportService:
    def __init__(self, bar_repository, *, job_repository=None, clock=None, as_of: date | None = None, discovery=None, archive_paths: Iterable[Path] = (), after_import=None) -> None:
        self.bar_repository = bar_repository
        self.jobs = job_repository
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.as_of = as_of or date.today()
        self.discovery = discovery
        self.archive_paths = tuple(Path(path).expanduser().resolve() for path in archive_paths)
        self.after_import = after_import
        self._stop_requested = False

    def default_paths(self) -> tuple[Path, ...]:
        candidates: list[Path] = []
        terminals = getattr(self.discovery, "terminals", ())
        ranked_terminals = sorted(
            (
                item for item in terminals
                if getattr(item, "vendor", None) == "tdx"
                and getattr(item, "status", None) == "ready"
                and getattr(item, "data_path", None) is not None
                and getattr(item, "selection_eligible", True)
            ),
            key=lambda item: (
                -float(getattr(item, "source_score", 0.0)),
                str(getattr(item, "install_path", "")).casefold(),
            ),
        )
        candidates.extend(Path(item.data_path) for item in ranked_terminals)
        active = getattr(self.discovery, "active_tdx_vipdoc", None)
        if active is not None:
            candidates.append(Path(active))
            root = Path(active).parent if Path(active).name.casefold() == "vipdoc" else Path(active)
            archive_root = root / "T0002"
            if archive_root.is_dir():
                candidates.append(archive_root)
        candidates.extend(self.archive_paths)
        return tuple(dict.fromkeys(path.expanduser().resolve() for path in candidates if path.exists()))

    def create_job(self, paths: Iterable[Path]):
        if self.jobs is None:
            raise RuntimeError("TDX import job repository is not configured")
        normalized = tuple(str(Path(path).expanduser().resolve()) for path in paths)
        return self.jobs.create_job(normalized)

    def current_job(self):
        return self.jobs.current() if self.jobs is not None else None

    def pause(self, job_id: str):
        if self.jobs is None:
            raise RuntimeError("TDX import job repository is not configured")
        current = self.jobs.get(job_id)
        if current.state not in {"pending", "running"}:
            raise ValueError("only a running or pending import job can be paused")
        self._stop_requested = True
        return self.jobs.update(job_id, state="paused", stage="paused")

    def resume(self, job_id: str):
        if self.jobs is None:
            raise RuntimeError("TDX import job repository is not configured")
        current = self.jobs.get(job_id)
        if current.state != "paused":
            raise ValueError("only a paused import job can be resumed")
        self._stop_requested = False
        return self.jobs.update(job_id, state="pending", stage="queued")

    def run(self, job_id: str):
        if self.jobs is None:
            raise RuntimeError("TDX import job repository is not configured")
        job = self.jobs.get(job_id)
        if job.state in {"completed", "failed", "paused"}:
            return job
        files, errors, temporary = self._collect_files(tuple(Path(item) for item in job.paths))
        imported = replaced = skipped = failed = len(errors)
        latest: date | None = None
        self.jobs.update(
            job_id, state="running", stage="scanning", total_files=len(files),
            processed_files=0, errors=errors,
        )
        try:
            for index, (candidate, symbol) in enumerate(files, start=1):
                if self._stop_requested:
                    return self.jobs.update(
                        job_id, state="paused", stage="paused", processed_files=index - 1,
                        imported_rows=imported, replaced_rows=replaced, skipped_rows=skipped,
                        failed_files=failed, latest_trade_date=latest.isoformat() if latest else None,
                    )
                self.jobs.update(
                    job_id, state="running", stage="importing", current_file=str(candidate),
                    processed_files=index - 1, total_files=len(files), imported_rows=imported,
                    replaced_rows=replaced, skipped_rows=skipped, failed_files=failed,
                )
                try:
                    bars = read_tdx_day_bars(candidate, symbol=symbol, as_of=self.as_of, limit=None)
                    if not bars:
                        raise ValueError("文件没有可验证的日线记录")
                    converted = [self._to_daily_bar(item) for item in bars]
                    added, upgraded, ignored = self.bar_repository.append_preferred(
                        converted, ("tdx-local-day", "tdx-package"),
                    )
                    imported += added
                    replaced += upgraded
                    skipped += ignored
                    latest = max(latest, bars[-1].trade_date) if latest else bars[-1].trade_date
                except ValueError as error:
                    failed += 1
                    errors.append(TdxImportError(
                        path=str(candidate), code="invalid_day_file",
                        detail=str(error) or "文件没有可验证的日线记录",
                    ))
                except Exception as error:
                    failed += 1
                    errors.append(TdxImportError(
                        path=str(candidate), code="file_import_failed",
                        detail=str(error) or type(error).__name__,
                    ))
                self.jobs.update(
                    job_id, state="running", stage="importing", processed_files=index,
                    total_files=len(files), imported_rows=imported, replaced_rows=replaced,
                    skipped_rows=skipped, failed_files=failed, current_file=str(candidate),
                    latest_trade_date=latest.isoformat() if latest else None, errors=errors,
                )
            completed = self.jobs.update(
                job_id, state="completed", stage="completed", processed_files=len(files),
                total_files=len(files), imported_rows=imported, replaced_rows=replaced,
                skipped_rows=skipped, failed_files=failed, current_file=None,
                latest_trade_date=latest.isoformat() if latest else None, errors=errors,
            )
            if self.after_import is not None:
                try:
                    self.after_import(latest)
                except Exception as error:
                    errors.append(TdxImportError(path="market-rebuild", code="rebuild_failed", detail=str(error) or type(error).__name__))
                    completed = self.jobs.update(job_id, errors=errors)
            return completed
        except Exception as error:
            errors.append(TdxImportError(
                path="tdx-import", code="import_failed",
                detail=str(error) or type(error).__name__,
            ))
            return self.jobs.update(
                job_id, state="failed", stage="failed", processed_files=max(0, index if "index" in locals() else 0),
                total_files=len(files), imported_rows=imported, replaced_rows=replaced,
                skipped_rows=skipped, failed_files=failed + 1, errors=errors,
            )
        finally:
            for path in temporary:
                shutil.rmtree(path, ignore_errors=True)

    def scan(self, paths: Iterable[Path]) -> TdxImportScan:
        normalized = tuple(dict.fromkeys(Path(path).expanduser().resolve() for path in paths))
        day_files, archives, readable = 0, 0, 0
        latest: date | None = None
        errors: list[TdxImportError] = []
        temporary: list[Path] = []
        try:
            for path in normalized:
                archives += self._archive_count(path)
                candidates = self._day_files(path, errors, temporary)
                for candidate in candidates:
                    if candidate.suffix.lower() != ".day":
                        continue
                    day_files += 1
                    symbol = _a_share_symbol(candidate)
                    if symbol is None:
                        continue
                    bars = read_tdx_day_bars(candidate, symbol=symbol, as_of=self.as_of, limit=1)
                    if bars:
                        readable += 1
                        latest = max(latest, bars[-1].trade_date) if latest else bars[-1].trade_date
            return TdxImportScan(
                scanned_paths=tuple(str(path) for path in normalized), day_files=day_files,
                archive_files=archives, readable_files=readable,
                latest_trade_date=latest.isoformat() if latest else None, errors=tuple(errors),
            )
        finally:
            for path in temporary:
                shutil.rmtree(path, ignore_errors=True)

    def import_now(
        self,
        paths: Iterable[Path],
        *,
        progress: Callable[[tuple[int, int, str]], None] | None = None,
        discovery_progress: Callable[[dict[str, object]], None] | None = None,
        extraction_progress: Callable[[tuple[int, int, str]], None] | None = None,
        incremental: bool = False,
        source: str = "tdx-local-day",
        batch_size: int = 1,
    ) -> TdxImportJob:
        if batch_size < 1:
            raise ValueError("批量导入文件数必须大于零")
        normalized = tuple(dict.fromkeys(Path(path).expanduser().resolve() for path in paths))
        files: list[tuple[Path, str, int]] = []
        errors: list[TdxImportError] = []
        temporary: list[Path] = []
        try:
            scan_started = time.monotonic()
            candidates: list[Path] = []
            for path in normalized:
                candidates.extend(self._day_files(path, errors, temporary, extraction_progress))
            total_scan_files = len(candidates)
            readable_files = 0
            for scan_index, candidate in enumerate(candidates, start=1):
                symbol = _a_share_symbol(candidate)
                if self._supported_symbol(symbol) is not None:
                    files.append((candidate, symbol, scan_index))
                elif discovery_progress is not None:
                    elapsed = max(0.001, time.monotonic() - scan_started)
                    rate = scan_index / elapsed
                    discovery_progress({
                        "scanned_files": scan_index,
                        "total_scan_files": total_scan_files,
                        "day_files": scan_index,
                        "readable_files": readable_files,
                        "current_file": str(candidate),
                        "scan_speed": rate,
                        "scan_eta_seconds": max(0.0, (total_scan_files - scan_index) / max(0.001, rate)),
                    })
            imported = replaced = skipped = 0
            failed = len(errors)
            latest: date | None = None
            total_files = len(files)
            latest_dates: dict[str, date | None] = {}
            if incremental and files:
                if discovery_progress is not None:
                    elapsed = max(0.001, time.monotonic() - scan_started)
                    rate = total_scan_files / elapsed if total_scan_files else 0.0
                    discovery_progress({
                        "phase": "scan_complete",
                        "scanned_files": total_scan_files,
                        "total_scan_files": total_scan_files,
                        "day_files": total_scan_files,
                        "readable_files": readable_files,
                        "current_file": None,
                        "scan_speed": rate,
                        "scan_eta_seconds": 0.0,
                    })
                symbols = list(dict.fromkeys(symbol for _candidate, symbol, _scan_index in files))
                latest_reader = getattr(self.bar_repository, "latest_dates", None)
                latest_dates = self._read_latest_dates_with_retry(
                    symbols,
                    latest_reader,
                    discovery_progress=discovery_progress,
                    scanned_files=total_scan_files,
                    total_scan_files=total_scan_files,
                    scan_started=scan_started,
                )
            pending: list[tuple[Path, str, list[DailyBar], date]] = []

            def flush_pending() -> None:
                nonlocal imported, replaced, skipped, failed, latest
                if not pending:
                    return
                groups = tuple(pending)
                pending.clear()
                try:
                    rows = [bar for _candidate, _symbol, bars, _latest in groups for bar in bars]
                    append_batch = getattr(
                        self.bar_repository,
                        "append_preferred_batch",
                        self.bar_repository.append_preferred,
                    )
                    added, upgraded, ignored = append_batch(
                        rows, ("tdx-local-day", "tdx-package"),
                    )
                    imported += added
                    replaced += upgraded
                    skipped += ignored
                    for _candidate, _symbol, _bars, group_latest in groups:
                        latest = max(latest, group_latest) if latest else group_latest
                except Exception:
                    if len(groups) == 1:
                        candidate, _symbol, _bars, _latest = groups[0]
                        failed += 1
                        errors.append(TdxImportError(
                            path=str(candidate), code="file_import_failed",
                            detail="数据库写入失败",
                        ))
                    else:
                        for candidate, _symbol, bars, group_latest in groups:
                            try:
                                added, upgraded, ignored = self.bar_repository.append_preferred(
                                    bars, ("tdx-local-day", "tdx-package"),
                                )
                                imported += added
                                replaced += upgraded
                                skipped += ignored
                                latest = max(latest, group_latest) if latest else group_latest
                            except Exception as error:
                                failed += 1
                                errors.append(TdxImportError(
                                    path=str(candidate), code="file_import_failed",
                                    detail=str(error) or type(error).__name__,
                                ))

            for index, (candidate, symbol, scan_index) in enumerate(files, start=1):
                try:
                    latest_stored = latest_dates.get(symbol)
                    start_date = latest_stored + timedelta(days=1) if latest_stored else None
                    bars = read_tdx_day_bars(
                        candidate, symbol=symbol, as_of=self.as_of, limit=None,
                        start_date=start_date,
                    )
                    if not bars:
                        if incremental and latest_stored is not None:
                            readable_files += 1
                            if discovery_progress is not None:
                                elapsed = max(0.001, time.monotonic() - scan_started)
                                scanned = scan_index
                                rate = scanned / elapsed
                                discovery_progress({
                                    "scanned_files": scanned,
                                    "total_scan_files": total_scan_files,
                                    "day_files": scanned,
                                    "readable_files": readable_files,
                                    "current_file": str(candidate),
                                    "scan_speed": rate,
                                    "scan_eta_seconds": max(0.0, (total_scan_files - scanned) / max(0.001, rate)),
                                })
                            if progress is not None:
                                progress((index, total_files, symbol))
                            continue
                        raise ValueError("文件没有可验证的日线记录")
                    converted = [self._to_daily_bar(item, source=source) for item in bars]
                    readable_files += 1
                    pending.append((candidate, symbol, converted, bars[-1].trade_date))
                    if len(pending) >= batch_size:
                        flush_pending()
                except ValueError as error:
                    failed += 1
                    errors.append(TdxImportError(
                        path=str(candidate), code="invalid_day_file",
                        detail=str(error) or "文件没有可验证的日线记录",
                    ))
                except Exception as error:
                    failed += 1
                    errors.append(TdxImportError(
                        path=str(candidate), code="file_import_failed",
                        detail=str(error) or type(error).__name__,
                    ))
                if discovery_progress is not None:
                    elapsed = max(0.001, time.monotonic() - scan_started)
                    scanned = scan_index
                    rate = scanned / elapsed
                    discovery_progress({
                        "scanned_files": scanned,
                        "total_scan_files": total_scan_files,
                        "day_files": scanned,
                        "readable_files": readable_files,
                        "current_file": str(candidate),
                        "scan_speed": rate,
                        "scan_eta_seconds": max(0.0, (total_scan_files - scanned) / max(0.001, rate)),
                    })
                if progress is not None:
                    progress((index, total_files, symbol))
            flush_pending()
            return TdxImportJob(
                job_id="tdx-import-sync", state="completed", stage="completed",
                paths=tuple(str(path) for path in normalized), total_files=len(files),
                processed_files=len(files), imported_rows=imported, replaced_rows=replaced,
                skipped_rows=skipped, failed_files=failed, current_file=None,
                latest_trade_date=latest.isoformat() if latest else None,
                percent=100 if files else 0, errors=tuple(errors),
                created_at=self.clock(), updated_at=self.clock(), finished_at=self.clock(),
            )
        finally:
            for path in temporary:
                try:
                    shutil.rmtree(path, ignore_errors=True)
                except OSError:
                    pass

    def _read_latest_dates_with_retry(
        self,
        symbols: list[str],
        latest_reader,
        *,
        discovery_progress: Callable[[dict[str, object]], None] | None,
        scanned_files: int,
        total_scan_files: int,
        scan_started: float,
        attempts: int = 5,
    ) -> dict[str, date | None]:
        for attempt in range(1, attempts + 1):
            try:
                if latest_reader is not None:
                    return latest_reader(symbols, self.as_of)
                coverage = self.bar_repository.coverage(symbols, self.as_of)
                return {
                    symbol: getattr(value, "latest_trade_date", None)
                    for symbol, value in coverage.items()
                }
            except Exception as error:
                if not self._is_database_unavailable(error) or attempt >= attempts:
                    if self._is_database_unavailable(error):
                        raise TdxLocalDatabaseUnavailable(
                            attempts=attempts,
                            scanned_files=scanned_files,
                            total_files=total_scan_files,
                        ) from error
                    raise
                delay = min(4.0, 0.25 * (2 ** (attempt - 1)))
                if discovery_progress is not None:
                    elapsed = max(0.001, time.monotonic() - scan_started)
                    discovery_progress({
                        "phase": "waiting_database",
                        "scanned_files": scanned_files,
                        "total_scan_files": total_scan_files,
                        "day_files": total_scan_files,
                        "readable_files": 0,
                        "current_file": None,
                        "scan_speed": scanned_files / elapsed if scanned_files else 0.0,
                        "scan_eta_seconds": delay,
                        "database_retry_attempt": attempt,
                        "database_retry_total": attempts,
                    })
                time.sleep(delay)

    @staticmethod
    def _is_database_unavailable(error: Exception) -> bool:
        message = str(error).casefold()
        return isinstance(error, (UnicodeDecodeError, OSError, RuntimeError)) and any(
            marker in message
            for marker in ("lock", "locked", "database", "duckdb", "占用", "不可读取")
        ) or isinstance(error, UnicodeDecodeError)

    def _day_files(
        self,
        path: Path,
        errors: list[TdxImportError],
        temporary: list[Path] | None = None,
        extraction_progress: Callable[[tuple[int, int, str]], None] | None = None,
    ) -> tuple[Path, ...]:
        if path.is_dir():
            candidates = list(path.rglob("*.day"))
            for archive in sorted(path.rglob("*.zip")):
                candidates.extend(self._day_files(archive, errors, temporary, extraction_progress))
            return tuple(sorted(dict.fromkeys(candidates)))
        if path.is_file() and path.suffix.lower() == ".day":
            return (path,)
        if path.is_file() and path.suffix.lower() == ".zip":
            target = Path(tempfile.mkdtemp(prefix="qibao-tdx-import-"))
            if temporary is not None:
                temporary.append(target)
            try:
                with zipfile.ZipFile(path) as archive:
                    root = target.resolve()
                    members = archive.infolist()
                    for member in members:
                        destination = (target / member.filename).resolve()
                        if destination != root and root not in destination.parents:
                            raise ValueError("archive member escapes temporary directory")
                    files = [member for member in members if not member.is_dir()]
                    total = len(files)
                    for index, member in enumerate(files, start=1):
                        destination = (target / member.filename).resolve()
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        with archive.open(member) as source, destination.open("wb") as output:
                            shutil.copyfileobj(source, output)
                        if extraction_progress is not None:
                            extraction_progress((index, total, member.filename))
                return tuple(sorted(target.rglob("*.day")))
            except (OSError, ValueError, zipfile.BadZipFile) as error:
                errors.append(TdxImportError(path=str(path), code="invalid_archive", detail=str(error) or "压缩包无法读取"))
                return ()
        errors.append(TdxImportError(path=str(path), code="path_unavailable", detail="路径不存在或不是支持的日线目录/压缩包"))
        return ()

    @staticmethod
    def _archive_count(path: Path) -> int:
        if path.is_file() and path.suffix.lower() == ".zip":
            return 1
        if path.is_dir():
            return sum(1 for item in path.rglob("*.zip") if item.is_file())
        return 0

    @staticmethod
    def _to_daily_bar(item, *, source: str = "tdx-local-day") -> DailyBar:
        return DailyBar.model_validate({
            "symbol": item.symbol, "trade_date": item.trade_date, "open": item.open,
            "high": item.high, "low": item.low, "close": item.close,
            "volume": item.volume, "amount": item.amount, "source": source,
        })

    def _collect_files(self, paths: tuple[Path, ...]):
        errors: list[TdxImportError] = []
        files: list[tuple[Path, str]] = []
        temporary: list[Path] = []
        for path in paths:
            for candidate in self._day_files(path, errors, temporary):
                symbol = _a_share_symbol(candidate)
                if self._supported_symbol(symbol) is not None:
                    files.append((candidate, symbol))
        return files, errors, temporary

    @staticmethod
    def _supported_symbol(symbol: str | None) -> str | None:
        if symbol is None:
            return None
        try:
            return validate_a_share_code(symbol)
        except ValueError:
            return None
