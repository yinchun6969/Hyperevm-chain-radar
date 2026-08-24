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
- Snapshot replay protection: `isSnapshot=true` messages are ignored after reconnect.
- Material perp-notional change P1 alerts.
- Wallet 360 persistence and Dashboard APIs.
- Doctor V0.3 checks HyperCore Info API and Read Precompile availability.

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
- LP withdrawal percentages remain observed priced-flow baselines rather than exact pool TVL.
- Native HYPE Core→EVM system-transaction detection remains best-effort.
