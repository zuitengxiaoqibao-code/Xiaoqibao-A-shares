from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import struct
import threading
import zipfile
from concurrent.futures import Executor, Future
from datetime import date, datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Callable
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx

from qibao_api.contracts.history_supplement import (
    HistorySupplementJob,
    HistorySupplementSourceAttempt,
    OfficialTdxArchiveInspection,
    OfficialTdxPackageInfo,
)
from qibao_api.contracts.instruments import validate_a_share_code
from qibao_api.gongbu.tdx_local_daily import TDX_DAY_RECORD, _a_share_symbol
from qibao_api.gongbu.tdx_local_import import TdxLocalDatabaseUnavailable


INFO_URL = "https://data.tdx.com.cn/vipdoc/_hsjdayinfo.js"
PACKAGE_URL = "https://data.tdx.com.cn/vipdoc/hsjday.zip"
_SIZE_PATTERN = re.compile(r'HSJDAY_SOFT_SIZE="([^"]+)"')
_TIME_PATTERN = re.compile(r'HSJDAY_SOFT_TIME="([^"]+)"')
logger = logging.getLogger(__name__)


def _friendly_repair_error(error: Exception) -> str:
    if isinstance(error, httpx.TimeoutException):
        return "数据源连接或读取超时"
    if isinstance(error, httpx.HTTPStatusError):
        return f"数据源返回 HTTP {error.response.status_code}，当前来源暂不可用"
    if isinstance(error, httpx.RequestError):
        return "无法连接数据源，请检查网络连接"
    if isinstance(error, PermissionError):
        return "无法写入数据目录，请检查文件占用及目录权限"
    if isinstance(error, UnicodeDecodeError):
        return "本地行情数据库暂时不可读取，可能正在被其他任务占用，请等待当前任务完成后重试"
    return str(error) or type(error).__name__


def _decode_official_metadata(response: httpx.Response) -> str:
    """Decode the vendor metadata without treating a binary/GBK response as UTF-8."""
    raw = response.content
    errors: list[UnicodeDecodeError] = []
    for encoding in ("utf-8-sig", "gb18030", "gbk"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError as error:
            errors.append(error)
    raise ValueError("通达信官方包元数据编码无法识别，请稍后重试") from errors[-1]


def parse_official_package_info(content: str) -> OfficialTdxPackageInfo:
    size = _SIZE_PATTERN.search(content)
    modified = _TIME_PATTERN.search(content)
    if size is None or modified is None:
        raise ValueError("通达信官方日线包元数据格式无法识别")
    try:
        observed = datetime.strptime(
            modified.group(1), "%Y-%m-%d %H:%M:%S",
        ).replace(tzinfo=ZoneInfo("Asia/Shanghai"))
    except ValueError as error:
        raise ValueError("通达信官方日线包日期无法识别") from error
    return OfficialTdxPackageInfo(size_label=size.group(1), modified_at=observed)


def _supported_symbol(member_name: str) -> str | None:
    symbol = _a_share_symbol(Path(PurePosixPath(member_name).name))
    if symbol is None:
        return None
    try:
        return validate_a_share_code(symbol)
    except ValueError:
        return None


def _latest_date(content: bytes, *, as_of: date) -> date | None:
    latest = None
    size = TDX_DAY_RECORD.size
    for offset in range(0, len(content) - size + 1, size):
        raw_date = struct.unpack_from("<I", content, offset)[0]
        try:
            value = date(raw_date // 10000, raw_date // 100 % 100, raw_date % 100)
        except (ValueError, OverflowError):
            continue
        if value <= as_of and (latest is None or value > latest):
            latest = value
    return latest


def inspect_official_archive(
    archive_path: Path,
    *,
    as_of: date,
) -> OfficialTdxArchiveInspection:
    day_count = supported_count = 0
    latest = None
    try:
        with zipfile.ZipFile(archive_path) as archive:
            bad_member = archive.testzip()
            if bad_member is not None:
                raise ValueError(f"压缩包校验失败：{bad_member}")
            for member in archive.infolist():
                normalized = PurePosixPath(member.filename.replace("\\", "/"))
                if normalized.is_absolute() or ".." in normalized.parts:
                    raise ValueError("压缩包包含不安全路径")
                if member.is_dir() or normalized.suffix.lower() != ".day":
                    continue
                day_count += 1
                if _supported_symbol(member.filename) is None:
                    continue
                supported_count += 1
                member_latest = _latest_date(archive.read(member), as_of=as_of)
                if member_latest is not None:
                    latest = max(latest, member_latest) if latest else member_latest
    except zipfile.BadZipFile as error:
        raise ValueError("下载文件不是有效的通达信日线压缩包") from error
    if supported_count == 0:
        raise ValueError("压缩包中没有可导入的 A 股日线文件")
    return OfficialTdxArchiveInspection(
        day_file_count=day_count,
        supported_file_count=supported_count,
        latest_trade_date=latest,
    )


class OfficialTdxPackageService:
    def __init__(
        self,
        *,
        cache_dir: Path,
        state_path: Path,
        tdx_import_service,
        history_service=None,
        client: httpx.Client | None = None,
        clock: Callable[[], datetime] | None = None,
        as_of: date | None = None,
        prepare_universe: Callable[[], None] | None = None,
    ) -> None:
        self.cache_dir = cache_dir
        self.state_path = state_path
        self.tdx_import_service = tdx_import_service
        self.history_service = history_service
        self.client = client or httpx.Client(
            timeout=httpx.Timeout(60, connect=15, read=60, write=60, pool=15),
            follow_redirects=True,
        )
        self._owns_client = client is None
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.as_of = as_of or datetime.now(ZoneInfo("Asia/Shanghai")).date()
        self._lock = threading.RLock()
        self.prepare_universe = prepare_universe
        self._accepting_jobs = True

    def start_job(self, executor: Executor) -> HistorySupplementJob:
        """Persist and submit together; never leave a rejected job looking active."""
        with self._lock:
            if not self._accepting_jobs:
                raise RuntimeError("修复服务正在关闭，请重新启动程序后重试")
            job = self._create_job_locked()
            try:
                future = executor.submit(self.run, job.job_id)
            except Exception:
                logger.exception("history repair submission failed job_id=%s", job.job_id)
                self._fail_background_job(job.job_id, "submit_failed",
                    "后台修复任务未能启动，执行器可能已关闭；请重新启动程序后重试。已有数据和缓存已保留。")
                raise
            future.add_done_callback(lambda completed: self._background_done(job.job_id, completed))
            return job

    def stop_accepting_jobs(self) -> None:
        with self._lock:
            self._accepting_jobs = False

    def _background_done(self, job_id: str, future: Future) -> None:
        # This also runs when an accepted task is cancelled before run() starts.
        try:
            if future.cancelled():
                self._fail_background_job(job_id, "task_cancelled",
                    "后台修复任务因程序关闭而取消；已有数据和缓存已保留，请重新启动程序后重试。")
                return
            error = future.exception()
            if error is not None:
                logger.error("history repair worker failed job_id=%s", job_id,
                    exc_info=(type(error), error, error.__traceback__))
                self._fail_background_job(job_id, "worker_failed",
                    f"后台修复任务意外退出：{_friendly_repair_error(error)}；已有数据和缓存已保留，可重新执行修复。")
        except Exception:
            logger.exception("history repair completion recording failed job_id=%s", job_id)

    def _fail_background_job(self, job_id: str, stage: str, detail: str) -> HistorySupplementJob | None:
        with self._lock:
            job = self.current_job()
            if job is None or job.job_id != job_id or job.state not in {"pending", "running"}:
                return job
            attempts = tuple(item.model_copy(update={
                "state": "failed" if item.state == "running" else "skipped",
                "detail": detail, "observed_at": self._now(),
            }) if item.state in {"pending", "running"} else item for item in job.source_attempts)
            return self._update(job, state="failed", stage="failed", error_stage=stage,
                error_detail=detail, finished_at=self._now(), source_attempts=attempts)

    def create_job(self) -> HistorySupplementJob:
        with self._lock:
            return self._create_job_locked()

    def _create_job_locked(self) -> HistorySupplementJob:
        current = self.current_job()
        if current is not None and current.state in {"pending", "running"}:
            raise ValueError("已有官方日线补齐任务正在执行")
        # Migrate evidence from the preceding counts-only release. The archive
        # is still hashed and matched against vendor metadata before reuse.
        if (current is not None and current.package_path and current.package_sha256
                and current.package_modified_at and current.final_target_date
                and current.failed_files == 0
                and any(item.source == "tdx_official" and item.state == "completed" for item in current.source_attempts)):
            package = Path(current.package_path)
            if package.is_file() and package.resolve().parent == self.cache_dir.resolve():
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                receipt = self.cache_dir / "last-import.json"
                temporary = receipt.with_suffix(".tmp")
                temporary.write_text(json.dumps({"modified_at": current.package_modified_at.isoformat(),
                    "target_date": current.final_target_date.isoformat(), "size": package.stat().st_size,
                    "sha256": current.package_sha256}), encoding="utf-8")
                temporary.replace(receipt)
        now = self._now()
        job = HistorySupplementJob(
            job_id=f"history-supplement-{uuid4().hex}",
            state="pending", stage="queued", percent=0,
            source_url=PACKAGE_URL, downloaded_bytes=0,
            day_file_count=0, supported_file_count=0,
            imported_rows=0, replaced_rows=0, skipped_rows=0, failed_files=0,
            source_attempts=self._initial_source_attempts(now),
            created_at=now, updated_at=now,
        )
        return self._save(job)

    def current_job(self) -> HistorySupplementJob | None:
        with self._lock:
            if not self.state_path.is_file():
                return None
            try:
                job = HistorySupplementJob.model_validate_json(
                    self.state_path.read_text(encoding="utf-8")
                )
            except (OSError, ValueError, json.JSONDecodeError):
                return None
            if self._is_legacy_database_lock_failure(job):
                # Older releases recorded a completed local scan as a terminal
                # 5% failure when DuckDB was locked. Reclassify that persisted
                # evidence so the UI cannot keep showing a stale failure after
                # the application has been upgraded.
                return self._save(job.model_copy(update={
                    "state": "partial",
                    "stage": "waiting_database",
                    "percent": max(6.0, job.percent),
                    "error_stage": None,
                    "error_detail": None,
                    "finished_at": None,
                    "result_detail": "本机日线扫描已完成，但本地行情数据库仍被占用，请释放占用后重新执行一键全面修复",
                    "updated_at": self._now(),
                }))
            return job

    @staticmethod
    def _is_legacy_database_lock_failure(job: HistorySupplementJob) -> bool:
        detail = " ".join(filter(None, (job.error_detail, job.result_detail)))
        normalized = detail.casefold()
        return (
            job.state == "failed"
            and job.scan_scanned_files > 0
            and job.scan_total_files is not None
            and job.scan_scanned_files >= job.scan_total_files
            and (
                "数据库暂时不可读取" in detail
                or "数据库仍被" in detail
                or "unicodedecodeerror" in normalized
                or "codec can't decode" in normalized
            )
        )

    def recover_interrupted(self) -> HistorySupplementJob | None:
        """Mark a job left running by a previous process as interrupted."""
        with self._lock:
            job = self.current_job()
            if job is None:
                return None
            return self._fail_background_job(job.job_id, "restart_recovery",
                "上次补齐任务随程序退出而中断，已保留校验通过的缓存包，请重新执行补齐。")

    def reconcile_current_job(self) -> HistorySupplementJob | None:
        """Refresh terminal jobs against today's real coverage contract."""
        job = self.current_job()
        if (
            job is None
            or job.state not in {"completed", "partial"}
            or self.history_service is None
        ):
            return job
        target_date = self.history_service.default_target_date()
        if not job.source_attempts:
            now = self._now()
            job = job.model_copy(update={
                "source_attempts": tuple(
                    HistorySupplementSourceAttempt(
                        source=source,
                        state="skipped",
                        detail="历史补齐任务未记录该来源的分阶段证据",
                        observed_at=now,
                    )
                    for source in ("tdx_local", "tdx_official", "mootdx", "baidu")
                ),
            })
        return self._final_review(
            job,
            target_date,
            latest_trade_date=job.latest_trade_date,
            reconciliation=True,
        )

    def package_info(self) -> OfficialTdxPackageInfo:
        response = self.client.get(INFO_URL)
        response.raise_for_status()
        return parse_official_package_info(_decode_official_metadata(response))

    def _resolve_target_date(self) -> date:
        """Resolve the repair date without blocking the official package fallback."""
        if self.history_service is None:
            return self.as_of
        try:
            return self.history_service.default_target_date()
        except (UnicodeDecodeError, OSError, RuntimeError) as error:
            logger.warning(
                "历史数据库暂时不可读取，官方包补齐改用当前观测日 %s：%s",
                self.as_of,
                error,
            )
            return self.as_of

    @staticmethod
    def _file_sha256(
        path: Path,
        progress: Callable[[int, int], None] | None = None,
    ) -> str:
        digest = hashlib.sha256()
        total = path.stat().st_size
        processed = 0
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
                processed += len(block)
                if progress is not None:
                    progress(processed, total)
        return digest.hexdigest()

    def run(self, job_id: str) -> HistorySupplementJob:
        job = self.current_job()
        if job is None or job.job_id != job_id:
            raise KeyError(job_id)
        stage = "checking_metadata"
        try:
            job = self._update(job, state="running", stage=stage, percent=2)
            if self.prepare_universe is not None:
                job = self._update(job, source_attempts=self._set_source_attempt(
                    job, "a_share_universe", "running", "正在检查并补齐 A 股证券目录",
                ))
                try:
                    self.prepare_universe()
                    job = self._update(job, source_attempts=self._set_source_attempt(
                        job, "a_share_universe", "completed", "A 股证券目录已检查",
                    ))
                except Exception as error:
                    job = self._update(job, source_attempts=self._set_source_attempt(
                        job, "a_share_universe", "failed",
                        f"证券目录补齐失败：{_friendly_repair_error(error)}；继续尝试本机和官方日线包",
                    ))
            target_date = self._resolve_target_date()
            # A continuation must not download/unpack the same complete package
            # again. Saved metadata is evidence only when date, file and SHA all
            # still match; final coverage is always independently verified.
            receipt_path = self.cache_dir / "last-import.json"
            try:
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                receipt = {}
            local_paths = tuple(getattr(self.tdx_import_service, "default_paths", lambda: ())())
            if (receipt.get("target_date") == target_date.isoformat()
                    and len(str(receipt.get("sha256", ""))) == 64):
                # A prior successful full import exists; reuse is checked below.
                local_paths = ()
            if local_paths:
                stage = "scanning"
                job = self._update(
                    job, stage=stage, percent=4,
                    source_attempts=self._set_source_attempt(
                        job, "tdx_local", "running", "正在扫描并导入本机通达信日线",
                    ),
                )

                def local_scan_progress(value: dict[str, object]) -> None:
                    nonlocal job
                    scanned = max(0, int(value.get("scanned_files", 0) or 0))
                    total_value = value.get("total_scan_files")
                    total = int(total_value) if total_value is not None else None
                    ratio = scanned / total if total and total > 0 else 0
                    detail = f"已扫描 {scanned} 个文件"
                    if total and total > 0:
                        detail += f" / {total}"
                    else:
                        detail += " · 正在统计总量"
                    current_file = str(value.get("current_file") or "") or None
                    if current_file:
                        detail += f" · 当前 {Path(current_file).name}"
                    speed = value.get("scan_speed")
                    eta = value.get("scan_eta_seconds")
                    if speed is not None:
                        detail += f" · {float(speed):.1f} 文件/秒"
                    if eta is not None and total and total > scanned:
                        detail += f" · 预计剩余 {max(1, round(float(eta)))} 秒"
                    phase = str(value.get("phase") or "scanning")
                    if phase == "scan_complete":
                        progress_stage = "waiting_database"
                        detail = (
                            f"本机日线扫描已完成：共发现 {scanned} 个文件，"
                            "正在读取本地行情数据库增量范围"
                        )
                    elif phase == "waiting_database":
                        progress_stage = "waiting_database"
                        attempt = value.get("database_retry_attempt")
                        total_attempts = value.get("database_retry_total")
                        detail = "本机日线扫描已完成，正在等待本地行情数据库释放并自动重试"
                        if attempt is not None and total_attempts is not None:
                            detail += f"（第 {int(attempt)}/{int(total_attempts)} 次）"
                    elif phase in {"importing", "writing", "batch_committed"}:
                        progress_stage = "importing"
                        processed = int(value.get("processed_files", 0) or 0)
                        import_total = int(value.get("total_import_files", 0) or 0)
                        detail = f"已发现 {scanned} 个日线文件 · 已处理 {processed} / {import_total} 个 A 股文件"
                        if phase == "writing":
                            detail += f" · 正在提交 {int(value.get('pending_write_rows', 0) or 0):,} 行"
                    else:
                        progress_stage = "scanning"
                    counts = {
                        name: max(0, int(value[name] or 0))
                        for name in ("processed_files", "total_import_files", "imported_rows", "replaced_rows",
                                     "skipped_rows", "failed_files", "pending_write_rows")
                        if name in value
                    }
                    job = self._update(
                        job,
                        stage=progress_stage,
                        percent=(6 if phase in {"scan_complete", "waiting_database"} else min(5, 4 + ratio)),
                        scan_scanned_files=scanned,
                        scan_total_files=total,
                        scan_day_files=max(0, int(value.get("day_files", scanned) or 0)),
                        scan_readable_files=max(0, int(value.get("readable_files", 0) or 0)),
                        scan_current_file=current_file,
                        scan_speed=float(speed) if speed is not None else None,
                        scan_eta_seconds=float(eta) if eta is not None else None,
                        result_detail=detail,
                        **counts,
                    )

                try:
                    local_result = self.tdx_import_service.import_now(
                        local_paths, discovery_progress=local_scan_progress,
                        incremental=True, source="tdx-local-day", batch_size=256,
                    )
                except TdxLocalDatabaseUnavailable as error:
                    job = self._update(
                        job,
                        state="partial",
                        stage="partial",
                        percent=max(6, job.percent),
                        finished_at=self._now(),
                        error_stage="tdx_local_database",
                        error_detail=str(error),
                        result_detail=(
                            f"本机日线扫描已完成：共发现 {job.scan_scanned_files} 个文件，"
                            f"可读取 {job.scan_readable_files} 个；"
                            "本地行情数据库仍被其他任务占用，已暂停写入并保留扫描结果，请释放占用后重试"
                        ),
                        source_attempts=self._set_source_attempt(
                            job, "tdx_local", "failed",
                            "本机日线扫描已完成，但本地行情数据库仍被占用，等待释放后重试",
                        ),
                    )
                    return job
                local_state = "completed" if local_result.state == "completed" else "failed"
                job = self._update(
                    job,
                    stage="checking_cache",
                    percent=max(8, job.percent),
                    pending_write_rows=0, imported_rows=local_result.imported_rows,
                    replaced_rows=local_result.replaced_rows,
                    skipped_rows=local_result.skipped_rows,
                    failed_files=local_result.failed_files,
                    result_detail=(
                        f"本机扫描完成：共发现 {job.scan_day_files} 个日线文件，"
                        f"可读取 {job.scan_readable_files} 个"
                    ),
                    source_attempts=self._set_source_attempt(
                        job, "tdx_local", local_state,
                        f"本机增量新增 {local_result.imported_rows}，替换 {local_result.replaced_rows}，失败 {local_result.failed_files}",
                    ),
                )
            else:
                job = self._update(
                    job,
                    source_attempts=self._set_source_attempt(
                        job, "tdx_local", "skipped", "已有同目标日的完整包入库记录，优先续修缺口" if receipt else "未发现可读取的本机通达信日线目录",
                    ),
                )
            info = self.package_info()
            target = self.cache_dir / f"hsjday-{info.modified_at:%Y%m%d}.zip"
            if (self.history_service is not None and target.is_file()
                    and receipt.get("modified_at") == info.modified_at.isoformat()
                    and receipt.get("target_date") == target_date.isoformat()
                    and receipt.get("size") == target.stat().st_size):
                job = self._update(job, stage="validating_cache", phase_key="cache-reuse", percent=8,
                                   result_detail="校验已成功导入的官方缓存，随后只续修剩余缺口")
                def reuse_hash_progress(done, total):
                    nonlocal job
                    job = self._update(job, validated_bytes=done, total_validation_bytes=total)
                if self._file_sha256(target, reuse_hash_progress) == receipt.get("sha256"):
                    job = self._update(job, source_attempts=self._set_source_attempt(
                        job, "tdx_official", "skipped", "同一目标日官方包已成功入库且哈希复核一致，跳过重复解压和全量导入",
                    ))
                    stage = "online_repair"
                    job = self._run_online_repair(job, target_date)
                    return self._final_review(job, target_date, latest_trade_date=job.latest_trade_date)
            temporary = self.cache_dir / "hsjday.zip.part"
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            job = self._update(
                job, stage="checking_cache", percent=5,
                package_modified_at=info.modified_at,
                package_size_label=info.size_label,
            )
            inspection = None
            if target.is_file():
                try:
                    stage = "validating_cache"
                    job = self._update(job, stage=stage, percent=8)
                    inspection = inspect_official_archive(target, as_of=self.as_of)
                    downloaded = target.stat().st_size
                    total = downloaded
                    def cached_hash_progress(processed: int, validation_total: int) -> None:
                        nonlocal job
                        job = self._update(
                            job, validated_bytes=processed,
                            total_validation_bytes=validation_total,
                            percent=min(22, 8 + processed / max(1, validation_total) * 14),
                        )
                    package_sha256 = self._file_sha256(target, cached_hash_progress)
                    job = self._update(
                        job, percent=45, downloaded_bytes=downloaded,
                        total_bytes=total, package_sha256=package_sha256,
                    )
                except (OSError, ValueError, zipfile.BadZipFile):
                    target.unlink(missing_ok=True)
                    inspection = None
            if inspection is None:
                stage = "downloading"
                job = self._update(job, stage=stage, percent=5)
                digest = hashlib.sha256()
                downloaded = 0
                with self.client.stream("GET", PACKAGE_URL) as response:
                    response.raise_for_status()
                    raw_total = response.headers.get("Content-Length")
                    total = int(raw_total) if raw_total and raw_total.isdigit() else None
                    with temporary.open("wb") as handle:
                        for block in response.iter_bytes(chunk_size=1024 * 1024):
                            if not block:
                                continue
                            handle.write(block)
                            digest.update(block)
                            downloaded += len(block)
                            ratio = downloaded / total if total else 0
                            job = self._update(
                                job, downloaded_bytes=downloaded, total_bytes=total,
                                percent=min(38, 8 + ratio * 30),
                            )
                        handle.flush()
                        os.fsync(handle.fileno())
                if total is not None and downloaded != total:
                    raise ValueError("官方日线包下载字节数与服务器声明不一致")
                stage = "validating"
                job = self._update(
                    job, stage=stage, percent=38, downloaded_bytes=downloaded,
                    total_bytes=total,
                )
                def downloaded_hash_progress(processed: int, validation_total: int) -> None:
                    nonlocal job
                    job = self._update(
                        job, validated_bytes=processed,
                        total_validation_bytes=validation_total,
                        percent=min(45, 38 + processed / max(1, validation_total) * 7),
                    )
                package_sha256 = self._file_sha256(temporary, downloaded_hash_progress)
                if package_sha256 != digest.hexdigest():
                    raise ValueError("官方日线包下载哈希复核不一致")
                job = self._update(job, package_sha256=package_sha256)
                inspection = inspect_official_archive(temporary, as_of=self.as_of)
                temporary.replace(target)
            job = self._update(
                job,
                source_attempts=self._set_source_attempt(
                    job, "tdx_official", "running", "官方完整包已下载并校验，准备解压导入",
                ),
            )
            stage = "extracting"
            job = self._update(
                job, stage=stage, percent=46, package_path=str(target),
                day_file_count=inspection.day_file_count,
                supported_file_count=inspection.supported_file_count,
                latest_trade_date=inspection.latest_trade_date,
                total_extract_files=inspection.day_file_count,
            )
            def extraction_progress(value: tuple[int, int, str]) -> None:
                nonlocal job
                extracted, total_files, _name = value
                job = self._update(
                    job, stage="extracting", extracted_files=extracted,
                    total_extract_files=total_files,
                    percent=min(58, 46 + extracted / max(1, total_files) * 12),
                )

            def import_progress(value: tuple[int, int, str]) -> None:
                nonlocal job
                processed, total_files, _symbol = value
                ratio = processed / total_files if total_files else 0
                job = self._update(
                    job, stage="importing", phase_key="official-import", processed_files=processed,
                    total_import_files=total_files,
                    percent=min(78, 58 + ratio * 20),
                )

            package_rows_before = job.imported_rows
            package_replaced_before = job.replaced_rows
            package_skipped_before = job.skipped_rows

            def package_write_progress(value: dict[str, object]) -> None:
                nonlocal job
                if value.get("phase") not in {"importing", "writing", "batch_committed"}:
                    return
                job = self._update(
                    job, stage="importing",
                    imported_rows=package_rows_before + int(value.get("imported_rows", 0) or 0),
                    replaced_rows=package_replaced_before + int(value.get("replaced_rows", 0) or 0),
                    skipped_rows=package_skipped_before + int(value.get("skipped_rows", 0) or 0),
                    pending_write_rows=int(value.get("pending_write_rows", 0) or 0),
                    result_detail=(f"官方包已处理 {value.get('processed_files', 0)} / {value.get('total_import_files', 0)} 个文件"
                                   + (f" · 正在提交 {value.get('pending_write_rows', 0):,} 行" if value.get("phase") == "writing" else "")),
                )

            try:
                imported = self.tdx_import_service.import_now(
                    (target,), progress=import_progress,
                    extraction_progress=extraction_progress, incremental=True,
                    discovery_progress=package_write_progress, source="tdx-package", batch_size=256,
                )
            except TypeError as error:
                if "extraction_progress" not in str(error) and "progress" not in str(error):
                    raise
                imported = self.tdx_import_service.import_now(
                    (target,), progress=import_progress, incremental=True,
                    source="tdx-package", batch_size=256,
                )
            if imported.state != "completed":
                raise ValueError("官方日线包导入未完成")
            imported_latest = imported.latest_trade_date
            if isinstance(imported_latest, str):
                imported_latest = date.fromisoformat(imported_latest)
            job = self._update(
                job, pending_write_rows=0, imported_rows=package_rows_before + imported.imported_rows,
                replaced_rows=package_replaced_before + imported.replaced_rows,
                skipped_rows=package_skipped_before + imported.skipped_rows,
                failed_files=job.failed_files + imported.failed_files,
                source_attempts=self._set_source_attempt(
                    job, "tdx_official", "completed",
                    f"官方包新增 {imported.imported_rows}，替换 {imported.replaced_rows}，失败 {imported.failed_files}",
                ),
            )
            if imported.failed_files == 0:
                receipt_path.parent.mkdir(parents=True, exist_ok=True)
                receipt_tmp = receipt_path.with_suffix(".tmp")
                receipt_tmp.write_text(json.dumps({"modified_at": info.modified_at.isoformat(),
                    "target_date": target_date.isoformat(), "size": target.stat().st_size,
                    "sha256": job.package_sha256}), encoding="utf-8")
                receipt_tmp.replace(receipt_path)
            after_import = getattr(self.tdx_import_service, "after_import", None)
            if after_import is not None:
                after_import(imported_latest or inspection.latest_trade_date)
            stage = "online_repair"
            job = self._run_online_repair(job, target_date)
            stage = "final_review"
            return self._final_review(
                job, target_date,
                latest_trade_date=imported_latest or inspection.latest_trade_date,
            )
        except Exception as error:
            # Package metadata/download/validation failures must not prevent
            # independent online sources from repairing the actual gaps.
            detail = _friendly_repair_error(error)
            if stage not in {"online_repair", "final_review"}:
                failed_source = "tdx_local" if stage in {"scanning", "waiting_database"} else "tdx_official"
                job = self._update(job, source_attempts=self._set_source_attempt(
                    job, failed_source, "failed", detail,
                ))
            if self.history_service is not None and stage not in {"online_repair", "final_review"}:
                job = self._update(
                    job, stage="online_repair", percent=79,
                    result_detail=f"当前来源失败：{detail}；正在自动切换在线及后备来源",
                )
                try:
                    target_date = self._resolve_target_date()
                    job = self._run_online_repair(job, target_date)
                    return self._final_review(job, target_date, latest_trade_date=job.latest_trade_date)
                except Exception as fallback_error:
                    detail += f"；在线及后备补齐仍未完成：{_friendly_repair_error(fallback_error)}"
                    stage = "online_repair"
            for attempt in job.source_attempts:
                if attempt.state == "running":
                    job = self._update(job, source_attempts=self._set_source_attempt(
                        job, attempt.source, "failed", detail,
                    ))
            return self._update(
                job, state="failed", stage="failed", finished_at=self._now(),
                error_stage=stage, error_detail=detail,
            )

    def close(self) -> None:
        self.stop_accepting_jobs()
        if self._owns_client:
            self.client.close()

    def _update(self, job: HistorySupplementJob, **changes) -> HistorySupplementJob:
        if "percent" in changes:
            changes["percent"] = max(job.percent, changes["percent"])
        now = self._now()
        changes["updated_at"] = now
        candidate = job.model_copy(update=changes)
        stage = candidate.stage
        labels = {"scanning": "扫描本机文件", "importing": "导入日线", "downloading": "下载官方包",
                  "validating": "校验官方包", "validating_cache": "校验官方缓存", "extracting": "解压官方包",
                  "online_repair": "在线补齐剩余股票", "final_review": "最终覆盖复核"}
        done, total, unit = 0, None, "项"
        if stage == "scanning":
            done, total, unit = candidate.scan_scanned_files, candidate.scan_total_files, "文件"
        elif stage == "importing":
            done, total, unit = candidate.processed_files, candidate.total_import_files, "文件"
        elif stage == "downloading":
            done, total, unit = candidate.downloaded_bytes, candidate.total_bytes, "字节"
        elif stage in {"validating", "validating_cache"}:
            done, total, unit = candidate.validated_bytes, candidate.total_validation_bytes, "字节"
        elif stage == "extracting":
            done, total, unit = candidate.extracted_files, candidate.total_extract_files, "文件"
        elif stage == "online_repair":
            total, unit = candidate.online_total, "只"
            done = max(0, total - candidate.online_pending)
        key = f"{stage}:{candidate.phase_key if stage in {'importing', 'online_repair'} else ''}"
        previous_key = f"{job.stage}:{job.phase_key if job.stage in {'importing', 'online_repair'} else ''}"
        reset = key != previous_key or job.phase_started_at is None or done < job.phase_start_count
        started = now if reset else job.phase_started_at
        baseline = done if reset else job.phase_start_count
        elapsed = (now - started).total_seconds()
        delta = done - baseline
        rate = delta / elapsed if elapsed >= 2 and delta > 0 else None
        terminal = candidate.state in {"completed", "partial", "failed"}
        changes.update(phase_label=labels.get(stage, "准备与检查"), phase_started_at=started,
                       phase_start_count=baseline, phase_unit=unit,
                       phase_percent=round(min(100, done / total * 100), 1) if total else None,
                       phase_rate=rate if not terminal else None,
                       phase_eta_seconds=max(0, (total - done) / rate) if total and rate and not terminal else None)
        return self._save(job.model_copy(update=changes))

    def _save(self, job: HistorySupplementJob) -> HistorySupplementJob:
        with self._lock:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
            temporary.write_text(job.model_dump_json(indent=2), encoding="utf-8")
            temporary.replace(self.state_path)
        return job

    def _now(self) -> datetime:
        value = self.clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("官方日线补齐时钟必须包含时区")
        return value.astimezone(timezone.utc)

    def _online_source_names(self):
        extras = tuple(name for name, _ in getattr(self.history_service, "fallback_sources", ()))
        return tuple(dict.fromkeys((*extras, "mootdx", "baidu")))

    def _initial_source_attempts(self, now: datetime) -> tuple[HistorySupplementSourceAttempt, ...]:
        return tuple(
            HistorySupplementSourceAttempt(
                source=source, state="pending", detail=detail, observed_at=now,
            )
            for source, detail in (
                ("tdx_local", "等待扫描本机通达信日线"),
                ("tdx_official", "等待检查通达信官方完整包"),
                *((source, "等待在线修复剩余股票") for source in self._online_source_names()),
            )
        )

    def _set_source_attempt(
        self,
        job: HistorySupplementJob,
        source: str,
        state: str,
        detail: str,
    ) -> tuple[HistorySupplementSourceAttempt, ...]:
        now = self._now()
        updated = tuple(
            item.model_copy(update={"state": state, "detail": detail, "observed_at": now})
            if item.source == source else item
            for item in job.source_attempts
        )
        if not any(item.source == source for item in updated):
            updated += (HistorySupplementSourceAttempt(source=source, state=state, detail=detail, observed_at=now),)
        return updated

    def _run_online_repair(self, job: HistorySupplementJob, target_date: date) -> HistorySupplementJob:
        if self.history_service is None:
            for source in self._online_source_names():
                job = self._update(
                    job, source_attempts=self._set_source_attempt(
                        job, source, "skipped", "未配置全市场在线修复服务",
                    ),
                )
            return job
        stage = "online_repair"
        job = self._update(job, stage=stage, percent=79, result_detail="正在确认剩余缺口并自动尝试在线及后备来源")
        repair = self.history_service.create_target_repair(target_date)
        if repair is None:
            for source in self._online_source_names():
                job = self._update(
                    job, source_attempts=self._set_source_attempt(
                        job, source, "skipped", "当前没有需要在线修复的股票",
                    ),
                )
            return job
        job = self._update(
            job, stage=stage, percent=79, online_total=repair.total_count,
            online_pending=repair.pending_count,
            source_attempts=self._set_source_attempt(
                job, "mootdx", "running", "正在通过通达信在线日线修复剩余股票",
            ),
        )
        job = self._update(
            job, source_attempts=self._set_source_attempt(
                job, "baidu", "running", "通达信在线失败时自动切换百度历史 K 线",
            ),
        )
        for source in self._online_source_names():
            if source not in {"mootdx", "baidu"}:
                job = self._update(job, source_attempts=self._set_source_attempt(
                    job, source, "running", "正在按来源顺序尝试修复剩余股票，失败后自动切换",
                ))

        online_rows_before = job.imported_rows
        repository = getattr(self.history_service, "jobs", None)
        committed_before = sum(item.written_rows for item in repository.items(repair.job_id)) if repository is not None else 0
        def online_progress(value) -> None:
            nonlocal job
            processed = value.ready_count + value.failed_count + value.skipped_count
            repository = getattr(self.history_service, "jobs", None)
            rows = max(0, sum(item.written_rows for item in repository.items(repair.job_id)) - committed_before) if repository is not None else 0
            job = self._update(
                job, online_total=value.total_count, online_ready=value.ready_count,
                online_skipped=value.skipped_count,
                online_failed=value.failed_count, online_pending=value.pending_count,
                phase_key="online-tail" if value.pending_count <= max(200, value.total_count * 0.05) else "online-bulk",
                online_repaired_rows=rows, imported_rows=online_rows_before + rows,
                percent=min(94, 79 + processed / max(1, value.total_count) * 15),
            )

        if getattr(self.history_service, "fallback_sources", ()):
            completed = self.history_service.run(repair.job_id, progress=online_progress, comprehensive=True)
            if completed.failed_count and not completed.pause_requested:
                job = self._update(job, result_detail=f"首轮仍有 {completed.failed_count} 只未补齐，正在自动重试剩余股票", phase_key="online-retry")
                self.history_service.retry_failed(repair.job_id)
                completed = self.history_service.run(repair.job_id, progress=online_progress, comprehensive=True)
        else:
            completed = self.history_service.run(repair.job_id, progress=online_progress)
        repository = getattr(self.history_service, "jobs", None)
        items = repository.items(repair.job_id) if repository is not None else ()
        online_rows = max(0, sum(item.written_rows for item in items) - committed_before)
        job = self._update(job, online_repaired_rows=online_rows,
                           imported_rows=online_rows_before + online_rows)
        failure_detail = ""
        if completed.failed_count or completed.pending_count:
            failures = tuple(dict.fromkeys(item.error_code for item in items if item.error_code))
            labels = {
                "ReadTimeout": "读取数据源超时", "ConnectTimeout": "连接数据源超时",
                "ConnectError": "无法连接数据源", "DataSourceUnavailable": "在线来源未返回有效日线",
                "SourceAuthorizationError": "数据源尚未授权", "PermissionError": "数据目录不可写",
                "OSError": "网络或本地文件读取失败", "ValueError": "数据源返回内容校验失败",
            }
            failure_detail = "；失败原因：" + ("、".join(labels.get(code, code) for code in failures) if failures else "在线来源未返回足够的有效日线，剩余股票已保留")
            samples = [f"{item.symbol}: {item.error_detail}" for item in items if getattr(item, "error_detail", None)][:3]
            if samples:
                failure_detail += "；示例：" + "；".join(samples)
        job = self._update(job, source_attempts=self._set_source_attempt(
            job, "eltdx", "completed" if getattr(completed, "eltdx_ready_count", 0) else "skipped",
            f"通达信 eltdx 连接池成功 {getattr(completed, 'eltdx_ready_count', 0)} 只；与 mootdx 同属通达信上游，不计为独立交叉证据",
        ))
        job = self._update(
            job, online_total=completed.total_count, online_ready=completed.ready_count,
            online_skipped=completed.skipped_count,
            online_failed=completed.failed_count, online_pending=completed.pending_count,
            source_attempts=self._set_source_attempt(
                job, "mootdx", "completed" if completed.tdx_ready_count else "failed" if completed.failed_count or completed.pending_count else "skipped",
                f"通达信在线成功 {completed.tdx_ready_count} 只",
            ),
        )
        job = self._update(job, source_attempts=self._set_source_attempt(
            job, "tencent", "completed" if getattr(completed, "tencent_ready_count", 0) else "skipped",
            f"腾讯收盘日线成功 {getattr(completed, 'tencent_ready_count', 0)} 只；仅接收已收盘目标日，含实际成交额，不替代历史数据",
        ))
        job = self._update(job, source_attempts=self._set_source_attempt(
            job, "eastmoney", "completed" if getattr(completed, "eastmoney_ready_count", 0) else "skipped",
            f"东方财富独立日线成功 {getattr(completed, 'eastmoney_ready_count', 0)} 只；有限并发，自动重试及多源切换{failure_detail}",
        ))
        return self._update(
            job, source_attempts=self._set_source_attempt(
                job, "baidu", "completed" if completed.baidu_ready_count else "failed" if completed.failed_count or completed.pending_count else "skipped",
                f"百度后备成功 {completed.baidu_ready_count} 只；在线失败 {completed.failed_count} 只；待补 {completed.pending_count} 只{failure_detail}",
            ),
        )

    def _final_review(
        self,
        job: HistorySupplementJob,
        target_date: date,
        *,
        latest_trade_date: date | None,
        reconciliation: bool = False,
    ) -> HistorySupplementJob:
        now = self._now()
        # A later coverage check is not execution time for the historical job.
        finished_at = (job.finished_at or job.updated_at) if reconciliation else now
        if self.history_service is None:
            return self._update(
                job, state="completed", stage="completed", percent=100,
                latest_trade_date=latest_trade_date, finished_at=finished_at,
                result_detail="官方完整包已完成导入；当前运行环境未配置全市场覆盖复核。",
                error_stage=None, error_detail=None,
            )
        if not reconciliation:
            job = self._update(job, stage="final_review", percent=96)
        coverage = self.history_service.coverage(target_date)
        threshold_ready = (
            getattr(coverage, "universe_count", 0) >= 4000
            and coverage.dominant_trade_date == target_date
            and (coverage.dominant_date_coverage_percent or 0) >= 98
            and (coverage.coverage_percent or 0) >= 98
        )
        remaining = (self.history_service.repair_center(target_date, limit=1).total_gap_count
                     if hasattr(self.history_service, "repair_center") else coverage.missing_history_count)
        ready = threshold_ready and remaining == 0
        if ready:
            detail = "预期交易日、主导交易日和历史覆盖均已通过复核。"
            if getattr(coverage, "confirmed_suspended_count", 0):
                detail += f"已交叉核实 {coverage.confirmed_suspended_count} 只目标日停牌股票，无需伪造当日日线。"
        elif threshold_ready:
            detail = f"已达到 98% 可用覆盖标准，但仍有 {remaining} 只待核实或补齐；不代表全部修复成功。停牌股票可能没有当日日线，具体原因和缺口已保留，可继续续修。"
        elif getattr(coverage, "universe_count", 0) < 4000:
            detail = "A 股证券目录数量不足，无法确认全市场完整性；已保留可用日线，请检查证券目录来源后重试。"
        elif coverage.dominant_trade_date != target_date:
            detail = (
                f"主导交易日仍落后：预期 {target_date.isoformat()}，"
                f"实际 {coverage.dominant_trade_date or '无数据'}；剩余缺口已保留，可继续重试。"
            )
        else:
            detail = "主导交易日已更新，但覆盖率仍低于 98%；剩余缺口已保留，可继续重试。"
        changes = dict(state="completed" if ready else "partial",
            stage="completed" if ready else "partial", percent=100,
            latest_trade_date=latest_trade_date,
            final_target_date=coverage.target_date,
            final_dominant_trade_date=coverage.dominant_trade_date,
            final_dominant_coverage_percent=coverage.dominant_date_coverage_percent,
            final_history_coverage_percent=coverage.coverage_percent,
            remaining_gap_count=remaining,
            final_quality=coverage.quality, final_blockers=coverage.blockers,
            result_detail=detail, finished_at=finished_at,
            error_stage=None, error_detail=None,
        )
        if reconciliation:
            # Coverage may take seconds. A newly submitted repair must never
            # be replaced by the result of reviewing an earlier task.
            with self._lock:
                current = self.current_job()
                if (current is None or current.job_id != job.job_id
                        or current.updated_at != job.updated_at
                        or current.state not in {"completed", "partial"}):
                    return current or job
                return self._update(job, **changes)
        return self._update(job, **changes)
