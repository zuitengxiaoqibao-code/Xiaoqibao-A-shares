# Evidence-First Performance Loop Verification

Date: 2026-08-11
Branch: `codex/a-share-daily-research`

## Delivered

- Quant strategy snapshots remain date-scoped and versioned under `cache/quant-strategy.json`.
- Candidate factor calculations use the bounded in-process factor cache.
- Portable production candidate scans run in a Windows process pool using the same local DuckDB daily bars and factor rules. The API process only consumes a validated `CandidateBoard`.
- Same-day disk snapshots remain visible while overview/candidate refresh is pending or failed; the last real candidate list is not cleared.
- Smoke polling now rejects refresh requests over three seconds and candidate-list loss after a valid candidate has appeared. Smoke cleanup removes only frozen process-pool children belonging to its own EXE/PID.

## Verification Results

- API full suite: `1193 passed, 1 skipped` in `28.83s`.
- Web full suite: `523 passed` across `82` files.
- TypeScript/Vite production build: passed.
- UTF-8/mojibake scan: clean.
- `git diff --check`: passed (only existing LF/CRLF warnings from the dirty worktree).
- Portable EXE smoke: passed; window `280ms`, API ready `9935ms`, quant request `4ms`, professional probes `1041ms`.
- Continuous quant probe: `8` refreshes, maximum request `666ms`, `2` candidates retained on every response, no candidate drop.
- Final EXE SHA-256: `39BA1399DA8EB5BB7F8521EA0F331450C7149EF2994362347E6E263AEF3B6425`.

## Data and Process Boundaries

- Quant candidates in the release smoke came from the local market database and real factor computation; no random or placeholder values were introduced.
- Professional TDX probes remain honestly `unavailable` because the local professional plugin is not initialized; the UI keeps the reason instead of substituting ordinary quotes.
- `127.0.0.1:17709` remained owned by `TdxW.exe` PID `3336` throughout verification. The smoke process and its children were released; no TDX process was stopped or restarted.
- Portable `config`, `data`, `news`, `cache`, `logs`, `models`, `exports`, and `backups` directories were preserved during rebuild.

## Residual Risk

- The process-isolated candidate scan still takes several seconds in the background on a full 5,242-symbol local universe. It no longer blocks API requests; the progress state and previous snapshot remain visible while it runs.
- External sector fund-flow sampling can report a remote protocol disconnect. The service keeps the last valid local cache and exposes the degraded source state.

## Final Acceptance Rerun (2026-08-11)

- Rebuilt `dist/XiaoQiBao-Portable` with `scripts/build-portable.ps1 -SkipTests` after the full test suite; all persistent directories were retained.
- API full suite: `1193 passed, 1 skipped`.
- Web full suite: `523 passed` across `82` files.
- Production TypeScript/Vite build, UTF-8/mojibake scan, and `git diff --check`: passed.
- Release-data smoke: window `310ms`, API ready `9620ms`, verification `11434ms`; home `144ms`, overview `97ms`, quant `8ms`, professional probes `1042ms`.
- Quant strategy smoke status: `partial`, `2` real candidates, `85.00%` regime coverage; professional TDX probes remained `unavailable` with an explicit plugin-initialization reason.
- Continuous refresh probe: `8` requests, maximum `123ms`, `2` candidates retained on every response, snapshot source stayed `disk`.
- Final portable EXE SHA-256: `A80EBA528FDAF7B64B31CB50BAE5AFE38F3F89621DF9150253AB19B0AFA7E9E3`.
- Post-smoke process check: no `xiaoqibao.exe` process remained; TongdaXin `TdxW.exe` PID `3336` and its `tdxcef.exe` children remained running.
