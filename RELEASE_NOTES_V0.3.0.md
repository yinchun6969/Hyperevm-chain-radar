# HyperEVM Chain Radar V0.3.0 — Wallet 360 Intelligence

V0.3.0 turns the V0.2 smart-money flow radar into a persistent high-score wallet monitoring system.

## Highlights

- HyperCore account snapshots for high-score wallets:
  - perp account value / notional / margin / withdrawable / unrealized PnL
  - largest open perp position
  - HYPE / USDC and other spot balances
  - observed vault equity
- HyperEVM Read Precompile verification using raw ABI `eth_call`:
  - Spot Balance `0x...0801`
  - L1 Block Number `0x...0809`
  - Account Margin Summary `0x...080f`
  - Core User Exists `0x...0810`
- Dynamic high-score wallet WebSocket subscriptions:
  - `userFills`
  - `userNonFundingLedgerUpdates`
  - live subscribe/unsubscribe watchlist refresh; no scheduled reconnect gap
- Bounded reconnect recovery: only a short recent snapshot overlap is accepted, and persisted-event dedupe prevents old events from being re-alerted.
- HyperCore `tid` is part of fill identity so multiple partial fills from the same order/hash/millisecond are retained separately.
- Non-funding ledger USD extraction supports the official per-delta fields such as `usdc`, `usdcValue`, `requestedUsd`, `netWithdrawnUsd` and `liquidatedNtlPos` without mispricing generic token `amount` as USD.
- Material perp-notional change P1 alerts.
- Wallet 360 persistence and Dashboard APIs.
- Doctor V0.3 checks HyperCore Info API and Read Precompile availability.
- Required live CI smoke checks HyperEVM Chain ID, latest block, HyperCore mids, Wallet 360 REST response shapes and the L1 block precompile.

## Rate-limit design

The default configuration intentionally keeps Wallet 360 bounded:

- 12 REST-tracked wallets, score >= 60
- account + spot snapshots every 60 seconds
- vault refresh every 300 seconds
- 8 user-WebSocket wallets, score >= 70
- Read Precompile verification for only the top 3 wallets every 300 seconds

This keeps the enrichment layer from overwhelming HyperCore Info API limits or the EVM RPC used by the realtime scanner.

## Safety / semantics

- Read-only; no signing or private keys.
- Wallet Score / P0 / P1 are engineering monitoring priorities, not investment advice.
- REST and precompile values may represent different moments and are not required to match exactly.
- Current `AccountMarginSummary` ABI order is `accountValue`, `marginUsed`, `ntlPos`, `rawUsd`, matching the official `hyper-evm-lib` source used for V0.3 verification.
- LP withdrawal percentages remain observed priced-flow baselines rather than exact pool TVL.
- Native HYPE Core→EVM system-transaction detection remains best-effort.
