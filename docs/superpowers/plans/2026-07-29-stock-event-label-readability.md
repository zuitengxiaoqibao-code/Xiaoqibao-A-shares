# Stock Event Label Readability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace hard-to-read vertical Chinese K-line labels with numbered anchors, a horizontal event index, and a synchronized full-detail strip.

**Architecture:** Keep the verified timeline response and event-density selector unchanged. Derive one chronological numbered-event view model inside `StockEventKline.tsx`, reuse it for ECharts markers and React controls, and keep `selectedEventId` as the only selection source of truth. Add component-scoped CSS for the index and detail strip without introducing dependencies or global state.

**Tech Stack:** React 19, TypeScript 5.8, ECharts 5.6, Vitest, Testing Library, CSS.

## Global Constraints

- Plot only verified `market_news.occurred_at` events returned by the timeline API.
- Never plot `market_hotspot.observed_at` as an event occurrence time.
- Keep A-share direction colors: positive red, negative green, neutral gold, uncertain gray.
- Maximum plotted events: 12 on desktop and 3 at viewport widths of 700px or less.
- Non-trading-day events remain list-only and never receive a K-line number.
- Preserve stale-cache behavior and the existing backend response contract.
- Use UTF-8-safe edits and scan touched Chinese files for mojibake before completion.

---

### Task 1: Numbered K-line Event Model

**Files:**
- Modify: `apps/web/src/features/stock-timeline/StockEventKline.tsx`
- Test: `apps/web/src/features/stock-timeline/StockEventKline.test.tsx`

**Interfaces:**
- Consumes: `selectTimelineChartEvents(data, selectedEventId, maxEvents)` and `StockTimelineEvent`.
- Produces: `NumberedTimelineEvent = { event: StockTimelineEvent; number: string }`, `numberTimelineEvents(events)`, and mark-line labels containing only `01`, `02`, and later chronological numbers.

- [ ] **Step 1: Write failing tests for chronological numbering and non-trading-day exclusion**

```tsx
it("uses chronological two-digit anchors instead of vertical Chinese labels", () => {
  const option = stockTimelineOption(timeline(), "negative");
  const candle = (option.series as Array<Record<string, unknown>>)[0];
  const markLine = candle.markLine as { data: Array<{ name: string; label: { formatter: string } }> };

  expect(markLine.data.map((item) => item.label.formatter)).toEqual(["01", "02", "03"]);
  expect(markLine.data.map((item) => item.name)).not.toContain("weekend");
  expect(markLine.data.every((item) => !item.label.formatter.includes("\n"))).toBe(true);
});
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `pnpm --dir apps/web test -- StockEventKline.test.tsx`

Expected: FAIL because the existing marker formatters contain vertical Chinese text.

- [ ] **Step 3: Implement the numbered event model and simplify chart spacing**

```tsx
type NumberedTimelineEvent = {
  event: StockTimelineEvent;
  number: string;
};

function numberTimelineEvents(events: StockTimelineEvent[]): NumberedTimelineEvent[] {
  return events.map((event, index) => ({
    event,
    number: String(index + 1).padStart(2, "0"),
  }));
}

const numbered = numberTimelineEvents(selectTimelineChartEvents(data, selectedEventId, maxEvents));
// Marker formatter uses item.number; marker offset only separates same-day anchors.
// Price grid top changes from 224 to 36 because long vertical labels are removed.
```

- [ ] **Step 4: Run the focused test and verify GREEN**

Run: `pnpm --dir apps/web test -- StockEventKline.test.tsx`

Expected: PASS with all chart option tests green.

- [ ] **Step 5: Commit the independently testable chart change**

```bash
git add apps/web/src/features/stock-timeline/StockEventKline.tsx apps/web/src/features/stock-timeline/StockEventKline.test.tsx
git commit -m "feat: replace stock event labels with numbered anchors"
```

### Task 2: Event Index, Detail Strip, and Four-way Selection

**Files:**
- Modify: `apps/web/src/features/stock-timeline/StockEventKline.tsx`
- Test: `apps/web/src/features/stock-timeline/StockEventKline.test.tsx`

**Interfaces:**
- Consumes: the chronological `NumberedTimelineEvent[]`, `selectedEventId`, and complete `data.events` evidence list.
- Produces: `shortEventTitle(event): string`, default latest plotted selection, horizontal buttons with `aria-pressed`, selected detail region, and one selection handler shared by index and evidence list.

- [ ] **Step 1: Write failing tests for default selection and synchronized controls**

```tsx
it("defaults to the latest plotted event and synchronizes index, detail, and evidence", async () => {
  render(<StockEventKline symbol="600519" asOf="2026-07-28" load={vi.fn().mockResolvedValue(timeline())} />);

  const latest = await screen.findByRole("button", { name: /03.*渠道调研/ });
  expect(latest).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByRole("region", { name: "当前事件详情" })).toHaveTextContent("机构发布渠道调研纪要");

  fireEvent.click(screen.getByRole("button", { name: /02.*业绩压力/ }));
  expect(screen.getByRole("region", { name: "当前事件详情" })).toHaveTextContent("公司披露阶段性经营压力");
  expect(screen.getByText("公司披露阶段性经营压力").closest("button")).toHaveAttribute("aria-pressed", "true");
});

it("keeps non-trading-day evidence list-only", async () => {
  render(<StockEventKline symbol="600519" load={vi.fn().mockResolvedValue(timeline())} />);
  await screen.findByRole("heading", { name: "事件 K 线" });
  expect(screen.queryByRole("button", { name: /周末事件/ })).not.toBeInTheDocument();
  expect(screen.getByText("周末公开新闻").closest("button")).toHaveTextContent("非交易日·未落图");
});
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `pnpm --dir apps/web test -- StockEventKline.test.tsx`

Expected: FAIL because the index, default selection, and detail region do not exist.

- [ ] **Step 3: Implement the React index and detail strip**

```tsx
function shortEventTitle(event: StockTimelineEvent): string {
  const source = event.label.trim() || event.themes[0]?.trim() || event.headline.trim();
  return Array.from(source.replace(/\s+/g, " ")).slice(0, 12).join("");
}

const numberedChartEvents = useMemo(() => numberTimelineEvents(chartEvents), [chartEvents]);
const selectedEvent = data.events.find((event) => event.event_id === selectedEventId) ?? null;

// Render .stock-event-index before .stock-event-layout.
// Render one button per numbered plotted event with number/date/title/direction.
// Render .stock-event-detail after the index with full headline, timestamp,
// publisher, up to three themes, association confidence, AI confidence, and source link.
// Index and evidence buttons both call setSelectedEventId(event.event_id) and never toggle off.
```

- [ ] **Step 4: Preserve valid selection across refreshes**

```tsx
useEffect(() => {
  if (!data) return;
  const plottedIds = new Set(chartEvents.map((event) => event.event_id));
  setSelectedEventId((current) => {
    if (current && data.events.some((event) => event.event_id === current)) return current;
    return chartEvents.at(-1)?.event_id ?? null;
  });
}, [chartEvents, data]);
```

The actual effect must avoid an unused temporary set and must not reset selection merely because density ranking changes.

- [ ] **Step 5: Run the focused tests and verify GREEN**

Run: `pnpm --dir apps/web test -- StockEventKline.test.tsx`

Expected: PASS, including refresh-token and cached-data cases.

- [ ] **Step 6: Commit the interaction change**

```bash
git add apps/web/src/features/stock-timeline/StockEventKline.tsx apps/web/src/features/stock-timeline/StockEventKline.test.tsx
git commit -m "feat: add synchronized stock event index and detail"
```

### Task 3: Responsive Presentation and Verification

**Files:**
- Modify: `apps/web/src/app/theme.css`
- Test: `apps/web/src/features/stock-timeline/StockEventKline.test.tsx`

**Interfaces:**
- Consumes: `.stock-event-index`, `.stock-event-index-item`, `.stock-event-detail`, existing direction classes, and 700px/1500px breakpoints.
- Produces: wrapping desktop index, horizontally scrollable mobile index, 40px minimum controls, visible direction-colored focus/selection, and a chart area without the old label headroom.

- [ ] **Step 1: Add a failing structural test for accessible controls**

```tsx
it("exposes every plotted index item as a pressed-state button", async () => {
  render(<StockEventKline symbol="600519" load={vi.fn().mockResolvedValue(timeline())} />);
  await screen.findByRole("heading", { name: "事件 K 线" });
  expect(screen.getAllByRole("button", { name: /0[1-3]/ })).toHaveLength(3);
  expect(screen.getByRole("region", { name: "当前事件详情" })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the focused test and verify RED if semantics are incomplete**

Run: `pnpm --dir apps/web test -- StockEventKline.test.tsx`

Expected: FAIL until the index names and region semantics are complete.

- [ ] **Step 3: Add component-scoped responsive styles**

```css
.stock-event-index { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 6px; min-width: 0; }
.stock-event-index-item { min-height: 44px; min-width: 0; }
.stock-event-index-item[aria-pressed="true"] { border-color: var(--event-color); box-shadow: inset 0 0 0 1px var(--event-color); }
.stock-event-detail { display: grid; min-width: 0; border-block: 1px solid rgba(77, 104, 130, .34); }

@media (max-width: 700px) {
  .stock-event-index { display: flex; overflow-x: auto; overscroll-behavior-inline: contain; }
  .stock-event-index-item { flex: 0 0 min(82vw, 280px); }
}
```

Complete the declarations using existing theme variables, direction classes, focus visibility, text wrapping, and `prefers-reduced-motion` behavior.

- [ ] **Step 4: Run focused and full frontend verification**

Run: `pnpm --dir apps/web test -- StockEventKline.test.tsx`

Expected: focused tests PASS.

Run: `pnpm --dir apps/web test`

Expected: all frontend tests PASS.

Run: `pnpm --dir apps/web build`

Expected: TypeScript and Vite production build PASS.

- [ ] **Step 5: Scan touched Chinese files for encoding damage**

Run: `rg -n "\?\?\?|�|锟|烫烫|屯屯" apps/web/src/features/stock-timeline/StockEventKline.tsx apps/web/src/features/stock-timeline/StockEventKline.test.tsx apps/web/src/app/theme.css`

Expected: no matches.

- [ ] **Step 6: Verify desktop and mobile rendering in the running app**

Check `http://127.0.0.1:5173/a-shares?symbol=600519` at 1440x1000 and 390x844. Confirm nonblank SVG content, no horizontal page overflow, readable horizontal event text, three mobile anchors, synchronized selection color, and no console errors.

- [ ] **Step 7: Commit the verified responsive presentation**

```bash
git add apps/web/src/app/theme.css apps/web/src/features/stock-timeline/StockEventKline.test.tsx
git commit -m "style: improve stock event timeline readability"
```

