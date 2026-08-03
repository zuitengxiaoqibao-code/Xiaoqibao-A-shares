# TDX History And Finance Resilience Design

## Goal

Keep mootdx as the preferred A-share daily-bar and finance source while making
its failure path fast, deterministic, and safe. Preserve Baidu K-line as the
independent fallback and never store malformed or partly parsed market data.

## Evidence And Root Cause

- The installed dependency is mootdx 0.11.7. Its `StdQuotes.bars` API accepts
  `frequency`, and both frequency 4 and 9 are documented daily categories.
- Real calls for symbol `600519` returned empty bars for frequency 4 and 9 on
  every configured node. Finance returned a valid one-row snapshot on the same
  nodes, so TCP reachability is not sufficient proof of operation readiness.
- With mootdx's default `auto_retry=True`, one empty bars request took about
  4.3 seconds. The application then repeated that internal retry cycle on five
  nodes, producing about 23 seconds of delay before Baidu fallback.
- With `auto_retry=False`, the same empty request returned in about 0.13
  seconds, while finance still returned a valid snapshot in about 0.16 seconds.
- The real Baidu fallback returned 20 valid daily bars for `600519`, including
  the current China trading date, in about 0.44 seconds.

## Chosen Approach

The application remains the only retry owner. The default mootdx factory will
create node clients with `auto_retry=False` and a three-second socket timeout.
`TdxFailoverClient` will continue to probe and try every configured node once,
close every node client, reject empty results, and preserve aggregate failure
details. Injected test or custom factories retain their existing call contract.

Do not switch the daily request from frequency 9 to 4. Local dependency source
and real comparison show that the observed failure is not caused by the public
parameter name or by selecting 9 instead of 4.

## Data Quality Gates

`BaiduHistorySource` must reject a batch before returning any bars when:

- the result code is not zero;
- required keys are missing;
- a row has fewer values than the declared keys;
- a date is duplicated;
- date, OHLC, volume, or amount cannot be parsed;
- price is non-positive, volume or amount is negative, or OHLC bounds conflict.

The source validates the complete returned batch before applying the caller's
limit. It does not fill, infer, or replace missing values.

`TdxFinanceSource` must reject a non-empty transport response that produces no
usable observation fields. Valid partial snapshots remain allowed when they
contain at least one real finance or update field.

## User-Facing Behavior

The source order remains mootdx then Baidu. If all mootdx nodes return empty,
the existing sync report records those attempts and reports Baidu as the actual
source. A valid Baidu result is a successful fallback, not a generic data-link
failure. If Baidu is malformed too, no bars are written and the existing error
report exposes the failed source attempts.

## Testing And Acceptance

- Unit-test that the default mootdx factory disables internal retry and applies
  the socket timeout, while custom factories remain unchanged.
- Unit-test Baidu string/integer success codes, missing keys, short rows,
  duplicate dates, invalid OHLC, and atomic batch rejection.
- Unit-test metadata-only finance rejection and valid partial finance acceptance.
- Run focused tests, the complete API suite, Ruff, the web suite, and production
  build.
- Repeat real `600519` checks for TDX failover duration, finance fields, and
  Baidu current daily bars.
- Run strict UTF-8, mojibake, and `git diff --check` gates.

## Boundaries

This slice does not add accounts, positions, orders, broker connectivity,
simulated funds, or automated trading. It does not let AI alter source data,
deterministic actions, confidence, numbers, or risk gates.
