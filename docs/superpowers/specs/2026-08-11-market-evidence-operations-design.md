# Market Evidence and Operations Design

## Objective

Upgrade the existing desktop product from a collection of data pages into a measurable evidence workflow. Every market conclusion must expose its data watermark, selection path, evidence source, sample boundary, freshness, and failure reason. The Windows portable EXE remains the only user-facing delivery.

## Product Principles

- Real local data first. Missing data stays unavailable; no random, simulated, or proxy values may appear as fact.
- Cached pages remain interactive while refresh runs in the background. A refresh must not clear the previous complete snapshot.
- Red means A-share rise, improvement, or inflow. Green means fall, deterioration, or outflow. Structural categories use neutral colors.
- Every score must be traceable to source fields, formula version, observation time, and sample count.
- A zero-candidate result is valid only when the data watermark is complete enough to evaluate the rules.
- TongdaXin professional fields are optional. Their failure must not block the rest of the application.

## Architecture

The current FastAPI contracts, DuckDB daily-bar store, source-health operation log, date-scoped quant snapshot, company-research enrichment, news cache, backtest service, and React visualization primitives remain authoritative. New contracts are read models derived from these existing sources:

1. `MarketDataWatermark` summarizes universe coverage, dominant trade date, fragmented dates, missing history, and source state.
2. `CandidateFunnel` records deterministic counts at each candidate-filter stage and the most important exclusion reasons.
3. `EvidenceLedgerEntry` provides a uniform source/formula/time/sample contract for market, quant, research, and news conclusions.
4. `OperationsCenter` exposes background refresh jobs, cache inventory, persistent-directory status, and safe maintenance actions.

No UI request performs a full-universe scan synchronously. The UI reads the last verified snapshot and observes background refresh progress.

## User Experience

### Data Settings

The data-source health section is collapsed by default. Its summary remains visible and includes aggregate source state. Expanding it triggers the first detailed load; users can refresh manually without losing the previous result.

### Market Data Watermark

Data settings and quantitative analysis show the dominant trade date, universe size, ready-history count, coverage percentage, fragmented-latest count, and explicit blockers. The panel distinguishes source availability from field completeness.

### Candidate Funnel

The short-term strategy workbench shows a horizontal funnel:

`universe -> history ready -> factor ready -> regime match -> strategy match -> trigger ready -> candidates`

Each stage shows count, retention percentage, and exclusion count. A separate list shows deterministic exclusion reason totals. When the result is zero, the panel explains whether the reason is incomplete data or rules filtering a complete universe.

### Evidence Ledger

Reusable evidence drawers show source, operation, trade date, observed time, formula version, sample size, quality state, and limitations. They are attached to market scores, quant candidates, company research conclusions, and news impact labels.

### Strategy Evaluation

Backtest and quant pages expose closed-trade minimums, rolling performance, regime segments, validation/out-of-sample state, look-ahead checks, drawdown, Sharpe, and invalidation conditions. Metrics stay unavailable when sample gates fail.

### Company Research

The existing research page gains a compact comparison ledger: peer context, valuation scenario evidence, catalyst summary, contrary evidence, and explicit thesis invalidation. AI may summarize verified evidence but may not create missing figures or target prices.

### News Event Graph

The existing event K-line and news intelligence views share deduplicated event records. Each event exposes category, source count, linked stocks/sectors/themes, impact direction, confidence basis, and timestamp. Unverified impact remains neutral.

### Local Operations

Operations exposes background refresh state, cache inventory, database size, persistent-directory status, last successful update, safe cache cleanup, incremental refresh, and backup/restore evidence. Destructive actions require an explicit in-app command and never touch TongdaXin processes.

## Performance Budgets

- Desktop window visible in under 500 ms.
- Cached first screen visible in under 1 second.
- Cached primary-route navigation P95 under 150 ms.
- No synchronous full-market calculation on a UI request.
- Background refresh never replaces a complete snapshot with a pending or failed response.

## Acceptance

- The same-day daily-bar dominant-date coverage is visible and quantified.
- `factor_as_of` is explicit before a candidate result is treated as complete.
- Zero candidates always include funnel and exclusion evidence.
- Data-source health is collapsed by default and manually expandable.
- API/web suites, production build, UTF-8 scan, portable rebuild, release-data smoke, repeated refresh probe, persistent-directory checks, and TongdaXin process-boundary checks all pass.

