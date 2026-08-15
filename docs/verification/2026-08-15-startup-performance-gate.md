# Startup Performance Evidence Gate

## Scope

This change closes a previously unmeasured part of the historical backlog: repeatable cold/hot startup evidence. It does not change application data or infer performance from a missing measurement.

## Implementation

- `scripts/startup-performance.ps1` aggregates smoke records from a file or a log directory.
- `scripts/run-portable-smoke.ps1` writes one UTF-8 `startup-smoke-*.json` record per run and adds the latest metrics to the signed release quality gate.
- `scripts/verify-release-quality.ps1` rejects releases that omit or invalidate startup metrics.
- Pester covers cold/hot grouping, nearest-rank median/P95, missing timing, threshold failure and manifest rejection.

## Fresh verification

- PowerShell/Pester: `14 passed, 0 failed`.
- API: `1415 passed, 1 skipped, 5 warnings`.
- Web: `119 test files, 675 tests passed`.
- TypeScript/Vite production build: passed.
- Clean portable build: passed from commit `b6402ab2de5420ad820a7a107dde3b72d2a3ff5c`.
- Real release-data smoke, cold: window `74ms`, API `2730ms`, full verification `17244ms`.
- Real release-data smoke, hot: window `71ms`, API `2533ms`, full verification `14898ms`.
- Aggregated performance gate: `pass`; cold window max `79ms` across retained records, hot window median `68ms`, hot window P95 `71ms`, hot API median `2533ms`, hot API P95 `2588ms`.
- Restore drill: `34` databases, migration `1`, critical API `pass`.
- Release quality gate: `pass` with truthful domain warnings for quant strategy/company research partial coverage.
- Final EXE: `dist/XiaoQiBao-Portable/xiaoqibao.exe`, SHA-256 `3139D3A56AA0EF41F4E456EDC399BBB255507A38D8A0D31A6C90D3B2B986A768`.

## Data boundary

The release remains `ready` for the market overview, `partial` for quantitative candidates and company research, `unavailable` for portfolio risk without configured positions, and `unavailable` for unverified TongdaXin professional packages. No simulated values were added.
