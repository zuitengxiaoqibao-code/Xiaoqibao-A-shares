# Convertible Bond Glass Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the approved obsidian-glass visual system to all three convertible-bond views and standardize the site typography on Orbitron, JetBrains Mono, and explicit Chinese fallbacks.

**Architecture:** Keep all existing bond API contracts and loaders. Split the current monolithic view into a stateful workbench shell plus focused overview, task-flow, diagnosis-detail, and candidate-filter components; share a normalized task-card model so every view represents discovered, diagnosed, unavailable, and excluded bonds consistently.

**Tech Stack:** React 19, TypeScript 5.8, CSS, Lucide React, Vitest, Testing Library, Fontsource Orbitron and JetBrains Mono.

## Global Constraints

- Convertible bonds remain isolated from A-share selection, candidates, watchlists, sentiment, and first-limit-up rules.
- Use only real `BondDashboard`, `BondCandidates`, `BondDiagnosis`, and `BondDiagnosisBatch` values; never synthesize prices, scores, charts, or returns.
- Orbitron is limited to short display headings and navigation labels; JetBrains Mono handles body, data, inputs, buttons, and status text.
- Every font stack that can render Chinese must include `Microsoft YaHei UI`, `Microsoft YaHei`, and `sans-serif` fallbacks.
- Obsidian `#050807`, glass `rgba(14, 20, 19, 0.78)`, emerald `#18E985`, amber `#F0B85A`, and red `#FF5B67` define the bond palette.
- Preserve `tablist`, `tab`, `aria-selected`, `aria-busy`, `role="alert"`, and `role="status"` semantics.
- Support desktop three-column, intermediate two-column, and mobile single-column layouts; primary touch controls are at least 44px high.
- Respect `prefers-reduced-motion: reduce`.
- Edit Chinese source files with `apply_patch`; run mojibake scans after changes.

---

### Task 1: Site-wide typography roles

**Files:**
- Modify: `apps/web/src/app/theme.css`
- Test: `apps/web/src/app/typography.test.ts`

**Interfaces:**
- Consumes: Fontsource imports already present in `apps/web/src/app/App.tsx`.
- Produces: CSS variables `--font-display`, `--font-body`, and `--font-data`, plus global heading/control typography rules used by the bond workbench.

- [ ] **Step 1: Write the failing typography source test**

Create `apps/web/src/app/typography.test.ts`:

```ts
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

describe("site typography", () => {
  it("defines Orbitron and JetBrains Mono roles with Chinese fallbacks", () => {
    const css = readFileSync(new URL("./theme.css", import.meta.url), "utf8");
    expect(css).toContain('--font-display: "Orbitron", "Microsoft YaHei UI", "Microsoft YaHei", sans-serif');
    expect(css).toContain('--font-body: "JetBrains Mono", "Microsoft YaHei UI", "Microsoft YaHei", sans-serif');
    expect(css).toContain("font-family: var(--font-body)");
    expect(css).toMatch(/h1,\s*h2,\s*h3[^{]*\{[^}]*font-family:\s*var\(--font-display\)/s);
  });
});
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```powershell
pnpm --filter @qibao/web exec vitest run src/app/typography.test.ts
```

Expected: FAIL because the three font variables and global role rules do not exist.

- [ ] **Step 3: Add the font tokens and role rules**

At the top of `theme.css`, add:

```css
:root {
  --font-display: "Orbitron", "Microsoft YaHei UI", "Microsoft YaHei", sans-serif;
  --font-body: "JetBrains Mono", "Microsoft YaHei UI", "Microsoft YaHei", sans-serif;
  --font-data: "JetBrains Mono", Consolas, "Microsoft YaHei UI", "Microsoft YaHei", monospace;
  font-family: var(--font-body);
}

body, button, input, select, textarea { font-family: var(--font-body); }
h1, h2, h3 { font-family: var(--font-display); }
code, time, output, .eyebrow { font-family: var(--font-data); }
```

Replace site-level hard-coded `Consolas` and title font declarations only where they conflict with these roles. Do not change ECharts internal font settings in this task.

- [ ] **Step 4: Run the test and build**

Run:

```powershell
pnpm --filter @qibao/web exec vitest run src/app/typography.test.ts
pnpm --filter @qibao/web build
```

Expected: typography test PASS and TypeScript/Vite build exit 0.

- [ ] **Step 5: Commit only typography changes**

```powershell
git add apps/web/src/app/theme.css apps/web/src/app/typography.test.ts
git commit -m "style: standardize site typography roles"
```

### Task 2: Normalize convertible-bond task cards

**Files:**
- Create: `apps/web/src/features/convertible-bonds/taskCards.ts`
- Create: `apps/web/src/features/convertible-bonds/taskCards.test.ts`
- Modify: `apps/web/src/features/convertible-bonds/types.ts`

**Interfaces:**
- Consumes: `BondDashboard`, `BondCandidates`, and optional current `BondDiagnosis`.
- Produces:

```ts
export type BondTaskTone = "ready" | "pending" | "unavailable" | "excluded";
export type BondTaskCard = {
  code: string;
  name: string;
  linkedStockCode: string | null;
  stateLabel: string;
  reason: string | null;
  tone: BondTaskTone;
};
export function bondTaskCards(candidates: BondCandidates | null): BondTaskCard[];
```

- [ ] **Step 1: Write failing normalization tests**

Cover these exact mappings:

```ts
expect(bondTaskCards(input)).toEqual([
  expect.objectContaining({ code: "113065", stateLabel: "可观察", tone: "ready" }),
  expect.objectContaining({ code: "123064", stateLabel: "未诊断", tone: "pending" }),
  expect.objectContaining({ code: "110001", stateLabel: "数据不可用", tone: "unavailable" }),
  expect.objectContaining({ code: "127001", stateLabel: "风险排除", tone: "excluded" }),
]);
```

Also assert that a candidate item missing from `discovered` is appended once and that no price or score field exists on `BondTaskCard`.

- [ ] **Step 2: Run the test and verify RED**

```powershell
pnpm --filter @qibao/web exec vitest run src/features/convertible-bonds/taskCards.test.ts
```

Expected: FAIL because `taskCards.ts` does not exist.

- [ ] **Step 3: Implement deterministic normalization**

Use `discovered` as the identity/name source. Override matching `diagnosed` items present in `items` to `ready`; preserve `risk_excluded` as `excluded`; never infer availability from a missing reason. Deduplicate by six-digit code while preserving discovered order.

- [ ] **Step 4: Run the tests and verify GREEN**

```powershell
pnpm --filter @qibao/web exec vitest run src/features/convertible-bonds/taskCards.test.ts
```

Expected: all normalization tests PASS.

- [ ] **Step 5: Commit the normalized view model**

```powershell
git add apps/web/src/features/convertible-bonds/types.ts apps/web/src/features/convertible-bonds/taskCards.ts apps/web/src/features/convertible-bonds/taskCards.test.ts
git commit -m "refactor: normalize convertible bond task cards"
```

### Task 3: Build the glass workbench shell and task flow

**Files:**
- Create: `apps/web/src/features/convertible-bonds/BondWorkbenchShell.tsx`
- Create: `apps/web/src/features/convertible-bonds/BondTaskFlow.tsx`
- Create: `apps/web/src/features/convertible-bonds/BondWorkbenchShell.test.tsx`
- Modify: `apps/web/src/features/convertible-bonds/ConvertibleBondView.tsx`

**Interfaces:**
- Consumes: `BondTaskCard[]`, current code, current tab, and existing tab/change/select callbacks.
- Produces:

```ts
type BondWorkbenchShellProps = {
  tab: "overview" | "diagnosis" | "candidates";
  onTabChange: (tab: "overview" | "diagnosis" | "candidates") => void;
  dashboard: BondDashboard | null;
  taskCards: BondTaskCard[];
  selectedCode: string | null;
  onSelectTask: (code: string) => void;
  children: React.ReactNode;
  detail: React.ReactNode;
};
```

- [ ] **Step 1: Write failing shell tests**

Assert:

- the workbench region is named “可转债独立工作台”;
- all five summary cards display real dashboard counts;
- all three tabs retain `aria-selected` semantics;
- task buttons include code, name, and state in their accessible names;
- selecting `123064` invokes `onSelectTask("123064")`;
- no A-share wording such as “首次涨停” or “市场情绪” is rendered.

- [ ] **Step 2: Run the test and verify RED**

```powershell
pnpm --filter @qibao/web exec vitest run src/features/convertible-bonds/BondWorkbenchShell.test.tsx
```

Expected: FAIL because the shell and task-flow components do not exist.

- [ ] **Step 3: Implement the semantic shell**

Create a header, internal tabs, five summary cards, left command rail, central `BondTaskFlow`, and right `detail` rail. Render task cards as `<button type="button">`; the selected task receives `aria-pressed="true"`. The central stack may use CSS transforms, but DOM order and keyboard order must remain identical.

- [ ] **Step 4: Mount the shell from `ConvertibleBondView`**

Keep the existing state and loader functions. Load candidates once for the overview task flow after dashboard load; a candidate-load failure must not replace a successfully loaded dashboard. On task selection:

```ts
setCode(selectedCode);
setTab("diagnosis");
void inspect(selectedCode);
```

Do not publish the selected bond through the A-share instrument provider.

- [ ] **Step 5: Run shell and existing bond tests**

```powershell
pnpm --filter @qibao/web exec vitest run src/features/convertible-bonds/BondWorkbenchShell.test.tsx src/features/convertible-bonds/ConvertibleBondView.test.tsx
```

Expected: new shell tests and all existing behavior tests PASS.

- [ ] **Step 6: Commit the workbench structure**

```powershell
git add apps/web/src/features/convertible-bonds/BondWorkbenchShell.tsx apps/web/src/features/convertible-bonds/BondTaskFlow.tsx apps/web/src/features/convertible-bonds/BondWorkbenchShell.test.tsx apps/web/src/features/convertible-bonds/ConvertibleBondView.tsx
git commit -m "feat: add convertible bond glass workbench shell"
```

### Task 4: Split diagnosis and candidate detail panels

**Files:**
- Create: `apps/web/src/features/convertible-bonds/BondDiagnosisDetail.tsx`
- Create: `apps/web/src/features/convertible-bonds/BondCandidateControls.tsx`
- Create: `apps/web/src/features/convertible-bonds/BondDiagnosisDetail.test.tsx`
- Create: `apps/web/src/features/convertible-bonds/BondCandidateControls.test.tsx`
- Modify: `apps/web/src/features/convertible-bonds/ConvertibleBondView.tsx`

**Interfaces:**
- Consumes: existing `BondDiagnosis`, filter map, batch report, candidates, and callbacks.
- Produces: focused presentational components without network calls.

- [ ] **Step 1: Write failing diagnosis-detail tests**

Test `ready`, `stale_quote`, and `source_conflict` diagnoses. Assert the exact ordering: risk conclusion, key risks, metrics, evidence source/time, and beginner explanation. Assert that null pure-bond value renders “未知（缺少纯债价值）” and never `0`, `NaN`, or `Infinity`.

- [ ] **Step 2: Write failing candidate-control tests**

Assert all four labelled filters, “应用筛选”, and “诊断首批”; ensure coverage separately displays 未诊断、数据不可用、风险排除、可观察 without combining categories.

- [ ] **Step 3: Run both tests and verify RED**

```powershell
pnpm --filter @qibao/web exec vitest run src/features/convertible-bonds/BondDiagnosisDetail.test.tsx src/features/convertible-bonds/BondCandidateControls.test.tsx
```

Expected: FAIL because the new presentational components do not exist.

- [ ] **Step 4: Extract the existing real-data rendering**

Move diagnosis rendering and translation maps into `BondDiagnosisDetail.tsx`; move filters, batch report, and coverage rendering into `BondCandidateControls.tsx`. Keep network state and callbacks in `ConvertibleBondView.tsx`. Do not change API request arguments or backend types.

- [ ] **Step 5: Isolate out-of-order diagnosis results**

Add a `useRef(0)` request sequence in `ConvertibleBondView`. Increment before each diagnosis request and only apply `setDiagnosis`/`setError`/`setLoading` when the completing request still matches the latest sequence. Add a regression test that resolves the old request after the new one and expects the new bond to remain visible.

- [ ] **Step 6: Run all bond tests and verify GREEN**

```powershell
pnpm --filter @qibao/web exec vitest run src/features/convertible-bonds
```

Expected: all convertible-bond tests PASS.

- [ ] **Step 7: Commit detail extraction and request isolation**

```powershell
git add apps/web/src/features/convertible-bonds
git commit -m "refactor: isolate convertible bond workbench panels"
```

### Task 5: Apply the approved obsidian-glass responsive design

**Files:**
- Modify: `apps/web/src/app/theme.css`
- Test: `apps/web/src/features/convertible-bonds/BondWorkbenchShell.test.tsx`

**Interfaces:**
- Consumes: semantic class names from Tasks 3 and 4.
- Produces: scoped `.bond-workbench-*` visuals without changing A-share component styling.

- [ ] **Step 1: Add stable visual hooks to the shell test**

Assert that the root has `bond-glass-workbench`, the summary has `bond-workbench-summary`, the three-column body has `bond-workbench-grid`, and selected cards have `selected`. This test protects the CSS contract without testing pixel values.

- [ ] **Step 2: Run the shell test and verify RED**

Expected: FAIL until the stable class names are present.

- [ ] **Step 3: Implement the scoped desktop design**

Add bond-only CSS variables and styles for:

- obsidian radial/grid background;
- glass cards with silver inner edge;
- five summary cards;
- `240px / minmax(420px, 1fr) / minmax(270px, 330px)` workbench grid;
- central task stack with emerald selected card and silver inactive cards;
- amber pending and red excluded/unavailable semantics;
- restrained hover lift, visible focus, and overflow-safe text.

- [ ] **Step 4: Implement responsive rules**

At `max-width: 1180px`, use two columns and place the detail rail below the task flow. At `max-width: 800px`, use one column and convert the task stack into a horizontal scroll-snap row. At `max-width: 520px`, stack summary cards in two columns, filters in one column, and keep controls at least 44px high.

- [ ] **Step 5: Add reduced-motion behavior**

Under the existing reduced-motion query, remove task-card transform transitions and disable ambient glass animation. Selection must remain visually clear without motion.

- [ ] **Step 6: Run focused tests and production build**

```powershell
pnpm --filter @qibao/web exec vitest run src/features/convertible-bonds src/app/typography.test.ts
pnpm --filter @qibao/web build
```

Expected: all focused tests PASS and build exits 0.

- [ ] **Step 7: Commit the visual system**

```powershell
git add apps/web/src/app/theme.css apps/web/src/features/convertible-bonds
git commit -m "style: redesign convertible bond workbench"
```

### Task 6: Browser QA and complete verification

**Files:**
- Modify only if a verified visual or accessibility defect is found.

- [ ] **Step 1: Start the existing development environment**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

Open `/convertible-bonds` and inspect desktop, 900px, and 390px widths.

- [ ] **Step 2: Verify all three views manually**

Confirm total overview, diagnosis, and candidate pool share the same shell; task selection opens the correct code; no unverified numeric content appears; errors retain already verified data; keyboard focus is visible.

- [ ] **Step 3: Run the full web test suite**

```powershell
pnpm --filter @qibao/web test
```

Expected: all tests PASS.

- [ ] **Step 4: Run the production build**

```powershell
pnpm --filter @qibao/web build
```

Expected: TypeScript and Vite exit 0.

- [ ] **Step 5: Run encoding and diff checks**

```powershell
rg -n '�|\?{3,}' apps/web/src/features/convertible-bonds apps/web/src/app/theme.css
git diff --check
```

Expected: mojibake scan returns no matches and `git diff --check` exits 0.

- [ ] **Step 6: Review the final diff for asset isolation**

```powershell
git diff -- apps/web/src/features/convertible-bonds apps/web/src/app/theme.css apps/web/src/app/typography.test.ts
```

Confirm no A-share loaders, routes, selection keys, or contracts were added to the bond feature.
