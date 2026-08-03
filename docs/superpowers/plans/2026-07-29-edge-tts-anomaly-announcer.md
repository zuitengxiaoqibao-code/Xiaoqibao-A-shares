# Edge TTS Anomaly Announcer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn the market overview's anomaly voice broadcast into real Microsoft Edge TTS audio with persistent voice and rate settings.

**Architecture:** The local FastAPI process owns Edge TTS transport, validation, persistent settings, and MP3 cache. React requests synthesized audio, queues verified anomaly events while the voice-broadcast workspace is active, and plays each event once. Cloud or playback failures remain visible but never block market data.

**Tech Stack:** Python 3.12, FastAPI, edge-tts, React 19, TypeScript, pywebview, Vitest, pytest.

## Global Constraints

- Only verified A-share anomalies from the existing market overview may be announced.
- Voice IDs are restricted to a Chinese Edge TTS allowlist.
- Rate is restricted to -50 through +50 percent.
- Synthesized files are stored under the portable cache directory and may be deleted safely.
- The final deliverable is the rebuilt portable Windows EXE.

---

### Task 1: Backend speech settings and synthesis

**Files:**
- Create: `apps/api/src/qibao_api/speech/models.py`
- Create: `apps/api/src/qibao_api/speech/settings_repository.py`
- Create: `apps/api/src/qibao_api/speech/edge_tts_service.py`
- Create: `apps/api/src/qibao_api/routes/speech.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Modify: `apps/api/pyproject.toml`
- Test: `apps/api/tests/speech/test_settings_repository.py`
- Test: `apps/api/tests/speech/test_edge_tts_service.py`
- Test: `apps/api/tests/routes/test_speech.py`

- [ ] Write failing tests for defaults, persistence, validation, cache reuse, and audio responses.
- [ ] Run the focused tests and confirm failures are caused by missing speech modules.
- [ ] Implement the minimal repository, service, and route registration.
- [ ] Lock and install edge-tts, then run the focused tests to green.

### Task 2: React settings and anomaly playback

**Files:**
- Create: `apps/web/src/features/speech/types.ts`
- Create: `apps/web/src/features/speech/api.ts`
- Create: `apps/web/src/features/speech/AnomalyVoiceAnnouncer.tsx`
- Create: `apps/web/src/features/speech/AnomalyVoiceAnnouncer.test.tsx`
- Modify: `apps/web/src/features/data-settings/DataSettingsView.tsx`
- Modify: `apps/web/src/features/data-settings/DataSettingsView.test.tsx`
- Modify: `apps/web/src/features/market-overview/MarketOverviewView.tsx`
- Modify: `apps/web/src/features/market-overview/MarketOverviewView.test.tsx`
- Modify: `apps/web/src/features/dashboard/Dashboard.tsx`
- Modify: `apps/web/src/app/App.tsx`

- [ ] Write failing tests for voice/rate persistence, preview playback, activation, event deduplication, and deactivation cleanup.
- [ ] Run focused Vitest tests and confirm they fail for the missing UI and announcer.
- [ ] Implement the settings section, audio queue, status UI, and feature wiring.
- [ ] Run focused tests to green.

### Task 3: Portable verification

**Files:**
- Modify: `packaging/xiaoqibao.spec` only if PyInstaller does not collect edge-tts automatically.

- [ ] Run the UTF-8 and mojibake scan on touched Chinese files.
- [ ] Run complete API and web test suites.
- [ ] Back up portable persistent directories and stop the old EXE.
- [ ] Rebuild with `scripts/build-portable.ps1`, restore persistent data, and run `scripts/run-portable-smoke.ps1`.
- [ ] Launch the rebuilt EXE and verify speech settings plus a real MP3 response through its local API.
