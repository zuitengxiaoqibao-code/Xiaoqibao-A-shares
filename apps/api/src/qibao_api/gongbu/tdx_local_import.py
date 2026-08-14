from __future__ import annotations

import tempfile
import zipfile
import shutil
from collections.abc import Iterable
from datetime import date, datetime, timezone
from pathlib import Path

from qibao_api.contracts.bars import DailyBar
from qibao_api.contracts.tdx_import import TdxImportError, TdxImportJob, TdxImportScan
from qibao_api.gongbu.tdx_local_daily import _a_share_symbol, read_tdx_day_bars


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
                bars = read_tdx_day_bars(candidate, symbol=symbol, as_of=self.as_of, limit=None)
                if not bars:
                    failed += 1
                    errors.append(TdxImportError(path=str(candidate), code="invalid_day_file", detail="文件没有可验证的日线记录"))
                else:
                    converted = [self._to_daily_bar(item) for item in bars]
                    added, upgraded, ignored = self.bar_repository.append_preferred(
                        converted, ("tdx-local-day", "tdx-package"),
                    )
                    imported += added
                    replaced += upgraded
                    skipped += ignored
                    latest = max(latest, bars[-1].trade_date) if latest else bars[-1].trade_date
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
        except Exception:
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

    def import_now(self, paths: Iterable[Path]) -> TdxImportJob:
        normalized = tuple(dict.fromkeys(Path(path).expanduser().resolve() for path in paths))
        files: list[tuple[Path, str]] = []
        errors: list[TdxImportError] = []
        temporary: list[Path] = []
        try:
            for path in normalized:
                for candidate in self._day_files(path, errors, temporary):
                    symbol = _a_share_symbol(candidate)
                    if symbol is not None:
                        files.append((candidate, symbol))
            imported = replaced = skipped = 0
            failed = len(errors)
            latest: date | None = None
            for candidate, symbol in files:
                bars = read_tdx_day_bars(candidate, symbol=symbol, as_of=self.as_of, limit=None)
                if not bars:
                    failed += 1
                    errors.append(TdxImportError(path=str(candidate), code="invalid_day_file", detail="文件没有可验证的日线记录"))
                    continue
                converted = [self._to_daily_bar(item) for item in bars]
                added, upgraded, ignored = self.bar_repository.append_preferred(
                    converted, ("tdx-local-day", "tdx-package"),
                )
                imported += added
                replaced += upgraded
                skipped += ignored
                latest = max(latest, bars[-1].trade_date) if latest else bars[-1].trade_date
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

    def _day_files(self, path: Path, errors: list[TdxImportError], temporary: list[Path] | None = None) -> tuple[Path, ...]:
        if path.is_dir():
            candidates = list(path.rglob("*.day"))
            for archive in sorted(path.rglob("*.zip")):
                candidates.extend(self._day_files(archive, errors, temporary))
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
                    for member in archive.infolist():
                        destination = (target / member.filename).resolve()
                        if destination != root and root not in destination.parents:
                            raise ValueError("archive member escapes temporary directory")
                    archive.extractall(target)
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
    def _to_daily_bar(item) -> DailyBar:
        return DailyBar.model_validate({
            "symbol": item.symbol, "trade_date": item.trade_date, "open": item.open,
            "high": item.high, "low": item.low, "close": item.close,
            "volume": item.volume, "amount": item.amount, "source": "tdx-local-day",
        })

    def _collect_files(self, paths: tuple[Path, ...]):
        errors: list[TdxImportError] = []
        files: list[tuple[Path, str]] = []
        temporary: list[Path] = []
        for path in paths:
            for candidate in self._day_files(path, errors, temporary):
                symbol = _a_share_symbol(candidate)
                if symbol is not None:
                    files.append((candidate, symbol))
        return files, errors, temporary
