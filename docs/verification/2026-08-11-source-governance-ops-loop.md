# Source Governance and Operations Loop Verification

Date: 2026-08-11
Release: `dist/XiaoQiBao-Portable/xiaoqibao.exe`

## Automated verification

- API suite: `1197 passed, 1 skipped, 5 warnings`.
- Web suite: `525 passed / 83 files`.
- Web production build: passed (`tsc -b && vite build`). Existing Vite chunk-size warnings remain; they do not prevent the build.
- Portable rebuild: passed with `Build complete!`.
- `git diff --check`: passed. Git reported only its normal LF/CRLF conversion notices.
- UTF-8 scan: changed source files decode as UTF-8. The broad mojibake search found only historical scan examples inside older plan documents, not mojibake in source or current verification output.

## Portable smoke

Command:

```text
powershell -ExecutionPolicy Bypass -File scripts/run-portable-smoke.ps1 -Port 18765 -UseReleaseData
```

Observed:

- Desktop window visible: `284 ms`.
- API lifespan/health ready: `9718 ms`.
- Verification completed: `11897 ms`.
- Requests: home `149 ms`, market overview `101 ms`, quant strategy `432 ms`, TDX professional probes `1035 ms`.
- Market overview: `ready`.
- Source health: `ready`.
- Quant strategy: `partial`, coverage `85.00%`, real candidates `0`.
- TDX professional probes: `unavailable` for `Fn193`, `GP1`, `BK5`, `SC1`, and `GO1`; the API reports the actual initialization/call failure and does not synthesize rows.

## Quant refresh stability probe

The probe launched the final EXE on port `18766` using the persistent release data. Each of eight iterations requested market overview first, then quant strategy.

| Iterations | Overview | Quant | Candidate count | Scan states |
| --- | --- | --- | ---: | --- |
| 1-8 | `ready` | `partial` | `0` on every request | `pending`/`ready`, no false list replacement |

Request timings stayed below the endpoint guardrails (overview `17-332 ms`; quant `4-23 ms`). `factor_as_of` remained unavailable in the release data and was represented as unavailable rather than guessed. The previous real-candidate snapshot retention path is covered by API regression tests and was not bypassed by this probe.

## Release integrity and process boundary

- EXE SHA-256: `6761C1556353A97278BEC11559A571A77141D9FB277CCD5BB2CF476E8AB26B4F`.
- Preserved release directories: `config`, `data`, `news`, `cache`, `logs`, `models`, `exports`, `backups`.
- Persistent release data was not replaced during smoke or probe.
- After cleanup, no `xiaoqibao` process remained.
- Existing TongdaXin processes remained running: `TdxW.exe` and five `tdxcef.exe` processes under `D:\new_tdx_mock`.
- No TongdaXin process was closed, restarted, or controlled by the verification scripts.

## Residual limitations

The official Python TongdaXin professional interface is still unavailable on this machine because its professional plugin initialization/call fails. The product exposes this as `unavailable` with a reason; it does not fall back to fabricated data. Standard local/release data and source-health evidence remain available.
