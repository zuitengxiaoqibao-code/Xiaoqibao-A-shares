# 可复现发布与迁移回滚

便携发布清单记录源码 commit、工作树状态、依赖锁哈希、迁移版本、程序文件哈希、数据库文件大小与 SHA-256、八个持久目录以及 smoke 质量状态。

发布步骤：先运行全量测试和编码扫描，再提交源码，从 clean commit 执行 `scripts/build-portable.ps1`，启动 EXE 完成数据迁移，随后运行 `scripts/run-portable-smoke.ps1 -UseReleaseData`、`scripts/verify-migrations.ps1` 和 `scripts/verify-release-quality.ps1`。

回滚只使用 `BackupService` 生成且逐文件哈希通过的 `backup-*` 目录。`scripts/rollback-portable-data.ps1` 不会主动关闭任何程序；一树-A股观测台仍运行时会拒绝回滚，通达信不在该脚本的进程范围内。替换前的 `data` 目录会改名保留，便于二次恢复。

