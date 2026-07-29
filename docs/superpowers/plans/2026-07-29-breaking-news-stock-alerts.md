# Breaking News Stock Alerts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn verified breaking financial news into deduplicated, explainable A-share alerts shown consistently in market overview, today decision, stock detail, and the event K-line.

**Architecture:** Preserve the append-only news archive and add explicit association metadata plus a read-side alert projection. Deterministic rules establish stock/theme links and verification state; AI interpretation may enrich impact direction but cannot invent instruments or block raw verified news when unavailable.

**Tech Stack:** Python 3.12, FastAPI, Pydantic 2, SQLite, pytest, React 19, TypeScript, Vitest, Testing Library.

## Global Constraints

- Never generate sample news, sample prices, random scores, or fabricated source confirmations.
- Keep original publisher, URL, publication time, fetch time, content hash, and source count traceable.
- A macro or theme-only event must not become a direct stock alert without an independent stock-level link.
- Treat urgency and verification as independent dimensions.
- AI may explain direction and uncertainty but may not add stock symbols.
- Unverified events must not enter stock decision evidence or the event K-line.
- Use local TDX bars for K-line placement and retain non-trading-day events without forcing a false trade date.
- External Eastmoney requests remain serialized and rate-limited by the existing source implementation.
- After touching Chinese UI or data files, run mojibake scans, focused tests, full API/web tests, and the web production build.

---

### Task 1: Explicit Association Metadata In The Evidence Contract

**Files:**
- Modify: `apps/api/src/qibao_api/contracts/news.py`
- Modify: `apps/api/src/qibao_api/gongbu/news_repository.py`
- Modify: `apps/api/tests/contracts/test_news.py`
- Modify: `apps/api/tests/gongbu/test_news_repository.py`

**Interfaces:**
- Produces: `AssociationKind = Literal["direct", "context", "theme", "macro"]`.
- Extends: `NormalizedNewsEvent.association_kind` and `association_reasons`.
- Extends: `NewsCorrection` with the same correctable fields.

- [ ] **Step 1: Write failing contract tests**

```python
def test_event_requires_reason_for_direct_association():
    with pytest.raises(ValueError, match="association reasons"):
        make_event(
            affected_instruments=((AssetKind.A_SHARE, "600519"),),
            association_kind="direct",
            association_reasons=(),
        )

def test_macro_event_cannot_claim_instruments():
    with pytest.raises(ValueError, match="macro event"):
        make_event(
            affected_instruments=((AssetKind.A_SHARE, "600519"),),
            association_kind="macro",
            association_reasons=("global market",),
        )
```

Add a repository reconciliation test proving a system correction can update association kind/reasons while frozen citation fields remain immutable.

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run --project apps/api pytest apps/api/tests/contracts/test_news.py apps/api/tests/gongbu/test_news_repository.py -q`

Expected: FAIL because association fields are not defined.

- [ ] **Step 3: Extend contracts and repository corrections**

```python
AssociationKind = Literal["direct", "context", "theme", "macro"]

class NormalizedNewsEvent(BaseModel):
    association_kind: AssociationKind = "macro"
    association_reasons: tuple[NonBlank, ...] = ()

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_association(cls, value):
        if isinstance(value, dict) and "association_kind" not in value:
            instruments = tuple(value.get("affected_instruments") or ())
            confidence = Decimal(str(value.get("association_confidence", "0")))
            value = dict(value)
            value["association_kind"] = (
                "direct" if instruments and confidence >= Decimal("1")
                else "context" if instruments
                else "theme" if value.get("industries") or value.get("themes")
                else "macro"
            )
            if instruments:
                value["association_reasons"] = ("legacy_confidence_migration",)
        return value

    @model_validator(mode="after")
    def validate_association(self):
        if self.association_kind in {"direct", "context"} and not self.association_reasons:
            raise ValueError("direct/context association requires association reasons")
        if self.association_kind == "macro" and self.affected_instruments:
            raise ValueError("macro event cannot claim instruments")
        return self
```

Add both fields to `_CORRECTABLE_EVENT_FIELDS`. In `NewsCorrection`, define them as optional (`association_kind: AssociationKind | None = None`, `association_reasons: tuple[NonBlank, ...] | None = None`) and update `_apply_corrections` only when they are not `None`; an unrelated human correction must never reset association metadata. The before-validator above must keep all existing stored event JSON readable without clearing the local database, and the next deterministic reconciliation may replace `legacy_confidence_migration` with a precise reason.

- [ ] **Step 4: Run focused tests**

Run: `uv run --project apps/api pytest apps/api/tests/contracts/test_news.py apps/api/tests/gongbu/test_news_repository.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/qibao_api/contracts/news.py apps/api/src/qibao_api/gongbu/news_repository.py apps/api/tests/contracts/test_news.py apps/api/tests/gongbu/test_news_repository.py
git commit -m "feat(api): record explainable news associations"
```

### Task 2: Stock Names, Codes, Context, Themes, And Macro Classification

**Files:**
- Modify: `apps/api/src/qibao_api/a_shares/instrument_directory.py`
- Modify: `apps/api/src/qibao_api/gongbu/news_linking.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Modify: `apps/api/tests/a_shares/test_instrument_directory.py`
- Modify: `apps/api/tests/gongbu/test_news_linking.py`

**Interfaces:**
- Produces: `AShareInstrumentDirectory.alias_map() -> dict[tuple[AssetKind, str], tuple[str, ...]]`.
- Changes: `DeterministicNewsLinker` accepts a mapping or zero-argument alias provider.
- Produces: explicit association kind, reasons, and deterministic confidence.

- [ ] **Step 1: Write failing linker classification tests**

```python
def test_company_name_is_a_direct_link():
    linker = DeterministicNewsLinker(
        instrument_aliases=lambda: {(AssetKind.A_SHARE, "600519"): ("贵州茅台",)},
        industry_keywords={}, theme_keywords={},
    )
    event = linker.link(article(title="贵州茅台发布业绩公告"))
    assert event.association_kind == "direct"
    assert event.affected_instruments == ((AssetKind.A_SHARE, "600519"),)
    assert "company_alias:贵州茅台" in event.association_reasons

def test_theme_only_news_does_not_claim_a_stock():
    event = linker.link(article(title="人形机器人板块受关注"))
    assert event.association_kind == "theme"
    assert event.affected_instruments == ()
```

Also test code matching (`600519`), stock-source context (`context`), and unmatched overseas macro news (`macro`).

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run --project apps/api pytest apps/api/tests/gongbu/test_news_linking.py apps/api/tests/a_shares/test_instrument_directory.py -q`

Expected: FAIL because aliases are static/empty and the event has no association kind.

- [ ] **Step 3: Implement lazy aliases and classification**

`alias_map()` returns only locally observed six-digit A-share codes with non-empty names. The linker evaluates matches in this order: explicit code or company alias -> direct; symbol-specific source context -> context; industry/theme keyword only -> theme; none -> macro.

```python
confidence = {
    "direct": Decimal("1"),
    "context": Decimal("0.85"),
    "theme": Decimal("0.60"),
    "macro": Decimal("0"),
}[association_kind]
```

In `main.py`, pass a lazy provider so the directory can finish initialization before the first sync:

```python
instrument_aliases=lambda: application.state.a_share_instrument_directory.alias_map()
```

The provider must return `{}` if the directory is still warming up, without fabricating names.

- [ ] **Step 4: Run focused tests**

Run: `uv run --project apps/api pytest apps/api/tests/gongbu/test_news_linking.py apps/api/tests/a_shares/test_instrument_directory.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/qibao_api/a_shares/instrument_directory.py apps/api/src/qibao_api/gongbu/news_linking.py apps/api/src/qibao_api/main.py apps/api/tests/a_shares/test_instrument_directory.py apps/api/tests/gongbu/test_news_linking.py
git commit -m "feat(api): classify stock news associations"
```

### Task 3: Breaking Alert Read Model

**Files:**
- Create: `apps/api/src/qibao_api/contracts/news_alerts.py`
- Create: `apps/api/src/qibao_api/a_shares/news_alerts.py`
- Create: `apps/api/tests/a_shares/test_news_alerts.py`
- Modify: `apps/api/src/qibao_api/gongbu/news_repository.py`
- Modify: `apps/api/tests/gongbu/test_news_repository.py`

**Interfaces:**
- Produces: `VerificationState`, `Urgency`, `BreakingNewsAlert`, and `BreakingNewsAlertResponse`.
- Produces: `BreakingNewsAlertService.current(cutoff: datetime, *, symbol: str | None = None, limit: int = 30) -> BreakingNewsAlertResponse`.
- Produces repository helpers: `cluster_for_article(article_id)` and `latest_interpretations_by_event(event_ids, cutoff)`.

- [ ] **Step 1: Write failing alert projection tests**

```python
def test_multi_source_direct_event_becomes_breaking_alert(service):
    result = service.current(CUTOFF, symbol="600519")
    alert = result.alerts[0]
    assert alert.verification_state == "multi_source_confirmed"
    assert alert.urgency == "breaking"
    assert alert.source_count == 2
    assert alert.association_kind == "direct"
    assert alert.affected_symbols == ("600519",)

def test_theme_only_event_never_enters_symbol_alerts(service):
    assert service.current(CUTOFF, symbol="600519").alerts == ()
```

Add tests for pending single-source context, rejected/unverified exclusion, stale event tracking, AI degraded direction, and cutoff protection.

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run --project apps/api pytest apps/api/tests/a_shares/test_news_alerts.py apps/api/tests/gongbu/test_news_repository.py -q`

Expected: FAIL because the alert contract and service do not exist.

- [ ] **Step 3: Implement contracts and pure projection rules**

```python
class BreakingNewsAlert(BaseModel):
    event_id: str
    headline: str
    occurred_at: AwareDatetime
    verification_state: Literal["verified", "multi_source_confirmed", "pending", "unverified"]
    urgency: Literal["breaking", "tracking", "normal"]
    association_kind: AssociationKind
    association_reasons: tuple[str, ...]
    affected_symbols: tuple[AShareCode, ...]
    themes: tuple[str, ...]
    publishers: tuple[str, ...]
    source_urls: tuple[WebUrl, ...]
    source_count: int = Field(ge=1)
    impact_direction: Literal["positive", "negative", "neutral", "uncertain"]
    impact_confidence: Decimal | None = Field(default=None, ge=0, le=1)
    ai_degraded: bool
```

Use event review state and verified article sources for verification; use cluster membership for source discovery. Count independent sources by distinct `(publisher, canonical host)` pairs, not raw article rows or mirror URLs. `breaking` requires an event within 120 minutes plus direct/context association and verified/multi-source state. `tracking` covers older verified events or pending direct/context events. `normal` remains available to market-wide consumers but is omitted when `symbol` is supplied. AI interpretation may set direction only when not degraded.

- [ ] **Step 4: Run focused tests**

Run: `uv run --project apps/api pytest apps/api/tests/a_shares/test_news_alerts.py apps/api/tests/gongbu/test_news_repository.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/qibao_api/contracts/news_alerts.py apps/api/src/qibao_api/a_shares/news_alerts.py apps/api/src/qibao_api/gongbu/news_repository.py apps/api/tests/a_shares/test_news_alerts.py apps/api/tests/gongbu/test_news_repository.py
git commit -m "feat(api): project verified breaking news alerts"
```

### Task 4: Alert API And Reusable Frontend Card

**Files:**
- Modify: `apps/api/src/qibao_api/dependencies.py`
- Modify: `apps/api/src/qibao_api/main.py`
- Modify: `apps/api/src/qibao_api/routes/news.py`
- Modify: `apps/api/tests/routes/test_news.py`
- Create: `apps/web/src/features/news-alerts/types.ts`
- Create: `apps/web/src/features/news-alerts/api.ts`
- Create: `apps/web/src/features/news-alerts/api.test.ts`
- Create: `apps/web/src/features/news-alerts/BreakingNewsStrip.tsx`
- Create: `apps/web/src/features/news-alerts/BreakingNewsStrip.test.tsx`
- Modify: `apps/web/src/app/terminal.css`

**Interfaces:**
- Produces: `GET /api/v1/news/alerts?symbol=600519&limit=30`.
- Produces: `loadBreakingNewsAlerts(symbol?, signal?)`.
- Produces: `BreakingNewsStrip({ alerts, loading, error, onOpenAShare })`.

- [ ] **Step 1: Write failing API and component tests**

```python
def test_alert_route_filters_by_symbol(client):
    response = client.get("/api/v1/news/alerts?symbol=600519&limit=10")
    assert response.status_code == 200
    assert all("600519" in item["affected_symbols"] for item in response.json()["alerts"])
```

```tsx
it("shows urgency, verification, association reason, source count and original link", () => {
  render(<BreakingNewsStrip alerts={[alert]} loading={false} error={null} />);
  expect(screen.getByText("突发")).toBeInTheDocument();
  expect(screen.getByText("多源确认")).toBeInTheDocument();
  expect(screen.getByText("直接关联")).toBeInTheDocument();
  expect(screen.getByText("2 个来源")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "查看原始来源" })).toHaveAttribute("href", alert.source_urls[0]);
});
```

- [ ] **Step 2: Run tests and verify failure**

Run: `uv run --project apps/api pytest apps/api/tests/routes/test_news.py -q`

Run: `pnpm --dir apps/web test -- src/features/news-alerts`

Expected: FAIL because the route and frontend feature do not exist.

- [ ] **Step 3: Implement endpoint, loader, types, and accessible strip**

Validate `symbol` with `^\d{6}$` and `limit` from 1 to 100. Return an explicit `status`, `observed_at`, `alerts`, `sources`, and `warnings`. Render colors through semantic classes, but always include text labels for urgency, verification, association, direction, and unavailable AI state.

- [ ] **Step 4: Run focused tests**

Run: `uv run --project apps/api pytest apps/api/tests/routes/test_news.py -q`

Run: `pnpm --dir apps/web test -- src/features/news-alerts`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/qibao_api/dependencies.py apps/api/src/qibao_api/main.py apps/api/src/qibao_api/routes/news.py apps/api/tests/routes/test_news.py apps/web/src/features/news-alerts apps/web/src/app/terminal.css
git commit -m "feat: expose breaking news alert stream"
```

### Task 5: Market Overview, Today Decision, And Stock Detail Integration

**Files:**
- Modify: `apps/web/src/app/App.tsx`
- Modify: `apps/web/src/features/dashboard/Dashboard.tsx`
- Modify: `apps/web/src/features/dashboard/Dashboard.test.tsx`
- Modify: `apps/web/src/features/market-overview/MarketOverviewView.tsx`
- Modify: `apps/web/src/features/market-overview/MarketOverviewView.test.tsx`
- Modify: `apps/web/src/features/decision-workbench/TodayDecisionView.tsx`
- Modify: `apps/web/src/features/decision-workbench/TodayDecisionView.test.tsx`
- Modify: `apps/web/src/features/stock-cockpit/StockDecisionCockpit.tsx`
- Modify: `apps/web/src/features/stock-cockpit/StockDecisionCockpit.test.tsx`

**Interfaces:**
- Consumes: `loadBreakingNewsAlerts` and `BreakingNewsStrip` from Task 4.
- Preserves: existing market overview polling, decision loaders, selected-symbol context, and cockpit refresh behavior.

- [ ] **Step 1: Add failing placement and filtering tests**

```tsx
expect(screen.getByRole("region", { name: "突发事件" })).toBeInTheDocument();
expect(screen.getByRole("region", { name: "突发事件" })).toHaveTextContent("多源确认");
expect(loadAlerts).toHaveBeenCalledWith("600519", expect.any(AbortSignal));
```

Overview receives the market-wide stream. Today decision receives market-wide or selected-symbol alerts according to scope. Stock cockpit always requests the selected symbol and shows the newest qualifying alert above detailed evidence.

- [ ] **Step 2: Run focused frontend tests and verify failure**

Run: `pnpm --dir apps/web test -- src/features/dashboard/Dashboard.test.tsx src/features/market-overview/MarketOverviewView.test.tsx src/features/decision-workbench/TodayDecisionView.test.tsx src/features/stock-cockpit/StockDecisionCockpit.test.tsx`

Expected: FAIL because loaders and alert regions are not wired.

- [ ] **Step 3: Wire one loader through the existing composition root**

Add `loadBreakingNewsAlerts` once in `App.tsx`, pass it through `Dashboard`, and let each page own request cancellation and stale snapshot display. Do not fold alert calls into unrelated market or decision responses.

Place the alert strip after key status/metric bands and before the page's detailed work area. Limit overview to six alerts, today decision to four, and stock detail to the newest three.

- [ ] **Step 4: Run focused frontend tests**

Run: `pnpm --dir apps/web test -- src/features/dashboard/Dashboard.test.tsx src/features/market-overview/MarketOverviewView.test.tsx src/features/decision-workbench/TodayDecisionView.test.tsx src/features/stock-cockpit/StockDecisionCockpit.test.tsx`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/app/App.tsx apps/web/src/features/dashboard apps/web/src/features/market-overview apps/web/src/features/decision-workbench apps/web/src/features/stock-cockpit
git commit -m "feat(web): surface breaking alerts in decision pages"
```

### Task 6: Event K-Line Badges And End-To-End Degradation

**Files:**
- Modify: `apps/api/src/qibao_api/contracts/stock_timeline.py`
- Modify: `apps/api/src/qibao_api/a_shares/stock_timeline.py`
- Modify: `apps/api/tests/a_shares/test_stock_timeline.py`
- Modify: `apps/web/src/features/stock-timeline/types.ts`
- Modify: `apps/web/src/features/stock-timeline/StockEventKline.tsx`
- Modify: `apps/web/src/features/stock-timeline/StockEventKline.test.tsx`
- Modify: `apps/web/src/app/terminal.css`
- Create: `docs/verification/2026-07-29-breaking-news-alerts-check.md`

**Interfaces:**
- Extends: `StockTimelineEvent` with `association_kind`, `association_reasons`, `verification_state`, `source_count`, and `urgency`.
- Preserves: `mapped_trade_date`, event numbering, marker selection, and no-future-data cutoff.

- [ ] **Step 1: Write failing timeline enrichment tests**

```python
def test_timeline_exposes_verified_direct_breaking_metadata(service):
    event = service.get("600519", AS_OF, CUTOFF).events[0]
    assert event.association_kind == "direct"
    assert event.verification_state == "multi_source_confirmed"
    assert event.urgency == "breaking"
    assert event.source_count == 2
```

```tsx
expect(screen.getByRole("region", { name: "当前事件详情" })).toHaveTextContent("突发");
expect(screen.getByRole("region", { name: "当前事件详情" })).toHaveTextContent("多源确认");
expect(screen.getByText("直接关联")).toBeInTheDocument();
```

Retain tests proving unverified events are excluded, non-trading-day events are listed but not mapped, and AI-degraded events display uncertain direction.

- [ ] **Step 2: Run timeline tests and verify failure**

Run: `uv run --project apps/api pytest apps/api/tests/a_shares/test_stock_timeline.py -q`

Run: `pnpm --dir apps/web test -- src/features/stock-timeline/StockEventKline.test.tsx`

Expected: FAIL because timeline fields and badges are missing.

- [ ] **Step 3: Enrich timeline payload from the same alert projection rules**

Do not duplicate verification or urgency formulas inside the frontend. The service uses the alert projector for each eligible event and copies projection metadata into `StockTimelineEvent`. The chart marker remains numbered; urgency/verification/association appear in the horizontal index and selected detail strip.

- [ ] **Step 4: Run full verification**

Run: `uv run --project apps/api pytest apps/api/tests/contracts apps/api/tests/gongbu apps/api/tests/a_shares apps/api/tests/routes/test_news.py -q`

Run: `pnpm --dir apps/web test`

Run: `pnpm --dir apps/web build`

Expected: all commands exit 0.

Run the encoding scan:

```powershell
$bad = rg -n "\?{3,}|锟斤拷|ï¿½|Ã.|Â." apps/api/src apps/api/tests apps/web/src docs/verification
if ($LASTEXITCODE -eq 1) { Write-Output "mojibake scan clean"; exit 0 }
$bad; exit 1
```

- [ ] **Step 5: Browser acceptance and commit**

Verify real stored news on `/market-overview`, `/`, and `/a-shares?symbol=600519` at 1440x900 and 390x844. Confirm no duplicate event cards, original links open, theme-only items are labeled and do not impersonate direct stock news, unavailable AI does not hide verified facts, and K-line labels do not overlap.

```bash
git add apps/api/src/qibao_api/contracts/stock_timeline.py apps/api/src/qibao_api/a_shares/stock_timeline.py apps/api/tests/a_shares/test_stock_timeline.py apps/web/src/features/stock-timeline apps/web/src/app/terminal.css docs/verification/2026-07-29-breaking-news-alerts-check.md
git commit -m "feat: complete evidence-backed stock news alerts"
```
