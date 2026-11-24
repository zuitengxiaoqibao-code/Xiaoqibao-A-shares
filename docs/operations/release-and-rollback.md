# 可复现发布与迁移回滚

便携发布清单记录源码 commit、工作树状态、依赖锁哈希、构建工具链版本、迁移版本、程序文件哈希、数据库文件大小与 SHA-256、备份基线、八个持久目录、smoke 质量状态和恢复演练结果。清单使用 SHA-256 摘要签名；任何字段在签名后被修改，发布质量门禁都会拒绝交付。

发布步骤：

1. 运行 API、Web、PowerShell 全量测试、构建检查和编码扫描，并提交源码。
2. 从 clean commit 执行 `scripts/build-portable.ps1 -SkipTests`。构建会保留八个持久目录，生成初始清单并签名；此时恢复演练状态为 `pending`。
3. 执行 `scripts/run-portable-smoke.ps1 -UseReleaseData`。脚本使用真实便携数据验证窗口、关键 API 和数据状态，更新运行态数据库证据并重新签名。
4. 执行 `scripts/verify-restore-drill.ps1 -ReleaseRoot <release> -UpdateManifest`。脚本先验签，再把八个持久目录、Web 资源、清单和迁移版本复制到安全临时目录，校验数据库大小与哈希，并使用正式 EXE 对临时副本执行关键 API smoke。临时副本不会改写正式数据；成功结果写回正式清单并重新签名。
5. 执行 `scripts/verify-migrations.ps1 -ReleaseRoot <release>` 和 `scripts/verify-release-quality.ps1 -ReleaseRoot <release>`。签名无效、恢复演练未通过、数据库哈希不一致、迁移异常或关键域证据缺失时均阻断交付。

`-SkipApiProbe` 只用于恢复演练单元测试，不能用于正式发布验收。`run-portable-smoke.ps1 -PortableRootOverride <temp-root>` 只供恢复演练让正式 EXE 读取临时副本；该外部目录由调用方管理，smoke 不会删除或改写正式发布目录。

回滚只使用 `BackupService` 生成且逐文件哈希通过的 `backup-*` 目录。`scripts/rollback-portable-data.ps1` 不会主动关闭任何程序；易数-A股观测台仍运行时会拒绝回滚，通达信不在该脚本的进程范围内。替换前的 `data` 目录会改名保留，便于二次恢复。
