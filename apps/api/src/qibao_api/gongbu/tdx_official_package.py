from __future__ import annotations

import hashlib
import json
import os
import re
import struct
import threading
import zipfile
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


INFO_URL = "https://data.tdx.com.cn/vipdoc/_hsjdayinfo.js"
PACKAGE_URL = "https://data.tdx.com.cn/vipdoc/hsjday.zip"
_SIZE_PATTERN = re.compile(r'HSJDAY_SOFT_SIZE="([^"]+)"')
_TIME_PATTERN = re.compile(r'HSJDAY_SOFT_TIME="([^"]+)"')


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

    def create_job(self) -> HistorySupplementJob:
        current = self.current_job()
        if current is not None and current.state in {"pending", "running"}:
            raise ValueError("已有官方日线补齐任务正在执行")
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
                return HistorySupplementJob.model_validate_json(
                    self.state_path.read_text(encoding="utf-8")
                )
            except (OSError, ValueError, json.JSONDecodeError):
                return None

    def recover_interrupted(self) -> HistorySupplementJob | None:
        """Mark a job left running by a previous process as interrupted."""
        job = self.current_job()
        if job is None or job.state not in {"pending", "running"}:
            return job
        return self._update(
            job,
            state="failed",
            stage="failed",
            error_stage="restart_recovery",
            error_detail="上次补齐任务随程序退出而中断，已保留校验通过的缓存包，请重新执行补齐。",
            finished_at=self._now(),
        )

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
            job = self._update(
                job,
                source_attempts=tuple(
                    HistorySupplementSourceAttempt(
                        source=source,
                        state="skipped",
                        detail="历史补齐任务未记录该来源的分阶段证据",
                        observed_at=now,
                    )
                    for source in ("tdx_local", "tdx_official", "mootdx", "baidu")
                ),
            )
        return self._final_review(
            job,
            target_date,
            latest_trade_date=job.latest_trade_date,
        )

    def package_info(self) -> OfficialTdxPackageInfo:
        response = self.client.get(INFO_URL)
        response.raise_for_status()
        return parse_official_package_info(_decode_official_metadata(response))

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
            target_date = (
                self.history_service.default_target_date()
                if self.history_service is not None else self.as_of
            )
            local_paths = tuple(getattr(self.tdx_import_service, "default_paths", lambda: ())())
            if local_paths:
                stage = "scanning"
                job = self._update(
                    job, stage=stage, percent=4,
                    source_attempts=self._set_source_attempt(
                        job, "tdx_local", "running", "正在扫描并导入本机通达信日线",
                    ),
                )
                local_result = self.tdx_import_service.import_now(
                    local_paths, incremental=True, source="tdx-local-day", batch_size=256,
                )
                local_state = "completed" if local_result.state == "completed" else "failed"
                job = self._update(
                    job,
                    imported_rows=local_result.imported_rows,
                    replaced_rows=local_result.replaced_rows,
                    skipped_rows=local_result.skipped_rows,
                    failed_files=local_result.failed_files,
                    source_attempts=self._set_source_attempt(
                        job, "tdx_local", local_state,
                        f"本机增量新增 {local_result.imported_rows}，替换 {local_result.replaced_rows}，失败 {local_result.failed_files}",
                    ),
                )
            else:
                job = self._update(
                    job,
                    source_attempts=self._set_source_attempt(
                        job, "tdx_local", "skipped", "未发现可读取的本机通达信日线目录",
                    ),
                )
            info = self.package_info()
            target = self.cache_dir / f"hsjday-{info.modified_at:%Y%m%d}.zip"
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
                    job, stage="importing", processed_files=processed,
                    total_import_files=total_files,
                    percent=min(78, 58 + ratio * 20),
                )

            try:
                imported = self.tdx_import_service.import_now(
                    (target,), progress=import_progress,
                    extraction_progress=extraction_progress, incremental=True,
                    source="tdx-package", batch_size=256,
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
                job, imported_rows=job.imported_rows + imported.imported_rows,
                replaced_rows=job.replaced_rows + imported.replaced_rows,
                skipped_rows=job.skipped_rows + imported.skipped_rows,
                failed_files=job.failed_files + imported.failed_files,
                source_attempts=self._set_source_attempt(
                    job, "tdx_official", "completed",
                    f"官方包新增 {imported.imported_rows}，替换 {imported.replaced_rows}，失败 {imported.failed_files}",
                ),
            )
            after_import = getattr(self.tdx_import_service, "after_import", None)
            if after_import is not None:
                after_import(imported_latest or inspection.latest_trade_date)
            job = self._run_online_repair(job, target_date)
            return self._final_review(
                job, target_date,
                latest_trade_date=imported_latest or inspection.latest_trade_date,
            )
        except Exception as error:
            now = self._now()
            return self._update(
                job, state="failed", stage="failed", finished_at=now,
                error_stage=stage, error_detail=str(error) or type(error).__name__,
            )

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def _update(self, job: HistorySupplementJob, **changes) -> HistorySupplementJob:
        changes["updated_at"] = self._now()
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

    @staticmethod
    def _initial_source_attempts(now: datetime) -> tuple[HistorySupplementSourceAttempt, ...]:
        return tuple(
            HistorySupplementSourceAttempt(
                source=source, state="pending", detail=detail, observed_at=now,
            )
            for source, detail in (
                ("tdx_local", "等待扫描本机通达信日线"),
                ("tdx_official", "等待检查通达信官方完整包"),
                ("mootdx", "等待在线修复剩余股票"),
                ("baidu", "等待作为在线历史后备源"),
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
        return tuple(
            item.model_copy(update={"state": state, "detail": detail, "observed_at": now})
            if item.source == source else item
            for item in job.source_attempts
        )

    def _run_online_repair(self, job: HistorySupplementJob, target_date: date) -> HistorySupplementJob:
        if self.history_service is None:
            for source in ("mootdx", "baidu"):
                job = self._update(
                    job, source_attempts=self._set_source_attempt(
                        job, source, "skipped", "未配置全市场在线修复服务",
                    ),
                )
            return job
        stage = "online_repair"
        repair = self.history_service.create_target_repair(target_date)
        if repair is None:
            for source in ("mootdx", "baidu"):
                job = self._update(
                    job, source_attempts=self._set_source_attempt(
                        job, source, "skipped", "官方包导入后没有需要在线修复的股票",
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

        def online_progress(value) -> None:
            nonlocal job
            processed = value.ready_count + value.failed_count + value.skipped_count
            job = self._update(
                job, online_total=value.total_count, online_ready=value.ready_count,
                online_failed=value.failed_count, online_pending=value.pending_count,
                percent=min(94, 79 + processed / max(1, value.total_count) * 15),
            )

        completed = self.history_service.run(repair.job_id, progress=online_progress)
        job = self._update(
            job, online_total=completed.total_count, online_ready=completed.ready_count,
            online_failed=completed.failed_count, online_pending=completed.pending_count,
            source_attempts=self._set_source_attempt(
                job, "mootdx", "completed" if completed.tdx_ready_count else "skipped",
                f"通达信在线成功 {completed.tdx_ready_count} 只",
            ),
        )
        return self._update(
            job, source_attempts=self._set_source_attempt(
                job, "baidu", "completed" if completed.baidu_ready_count else "skipped",
                f"百度后备成功 {completed.baidu_ready_count} 只；在线失败 {completed.failed_count} 只",
            ),
        )

    def _final_review(
        self,
        job: HistorySupplementJob,
        target_date: date,
        *,
        latest_trade_date: date | None,
    ) -> HistorySupplementJob:
        now = self._now()
        if self.history_service is None:
            return self._update(
                job, state="completed", stage="completed", percent=100,
                latest_trade_date=latest_trade_date, finished_at=now,
                result_detail="官方完整包已完成导入；当前运行环境未配置全市场覆盖复核。",
                error_stage=None, error_detail=None,
            )
        job = self._update(job, stage="final_review", percent=96)
        coverage = self.history_service.coverage(target_date)
        ready = (
            coverage.dominant_trade_date == target_date
            and (coverage.dominant_date_coverage_percent or 0) >= 98
            and (coverage.coverage_percent or 0) >= 98
        )
        if ready:
            detail = "预期交易日、主导交易日和历史覆盖均已通过复核。"
        elif coverage.dominant_trade_date != target_date:
            detail = (
                f"主导交易日仍落后：预期 {target_date.isoformat()}，"
                f"实际 {coverage.dominant_trade_date or '无数据'}；剩余缺口已保留，可继续重试。"
            )
        else:
            detail = "主导交易日已更新，但覆盖率仍低于 98%；剩余缺口已保留，可继续重试。"
        return self._update(
            job, state="completed" if ready else "partial",
            stage="completed" if ready else "partial", percent=100,
            latest_trade_date=latest_trade_date,
            final_target_date=coverage.target_date,
            final_dominant_trade_date=coverage.dominant_trade_date,
            final_dominant_coverage_percent=coverage.dominant_date_coverage_percent,
            final_history_coverage_percent=coverage.coverage_percent,
            remaining_gap_count=coverage.missing_history_count,
            final_quality=coverage.quality, final_blockers=coverage.blockers,
            result_detail=detail, finished_at=now,
            error_stage=None, error_detail=None,
        )
