# HyperEVM Chain Radar V0.3.9

HyperEVM + HyperCore capital-flow, smart-money and Wallet 360 monitoring. V0.3.9 is the stable hardening release for the 0.3.x line and preserves the validated Wallet 360 monitoring semantics.

## V0.3.9 stable line

The core path remains:

**HyperCore trade → Core→EVM → HyperSwap BUY → LP ADD → wallet score → HyperCore Spot/Perp/Vault state → Read Precompile verification → persistent high-score wallet monitoring.**

Release hardening in V0.3.9:

- Central version metadata in `core/version.py` so Doctor and Supervisor cannot drift.
- CI keeps full Python compilation, all regression tests, live read-only HyperEVM/HyperCore smoke checks, and shell syntax validation.
- A public-config release guard verifies that sample Telegram credentials and Etherscan keys remain empty and that the dashboard defaults to `127.0.0.1`.
- Stable releases follow version branch → pull request → CI → main.

## Wallet 360

High-score wallets are enriched with:

- `clearinghouseState`: account value, perp notional, margin used, withdrawable amount, unrealized PnL and largest open position.
- `spotClearinghouseState`: HYPE / USDC and other spot balances.
- `userVaultEquities`: observed vault equity.
- HyperEVM Read Precompile dual-source verification.
- Dynamic `userFills` and `userNonFundingLedgerUpdates` WebSocket subscriptions.
- P1 alerts for material changes in observed perp notional exposure.
- Wallet 360 dashboard and `/api/wallet360` endpoints.

## Read Precompile verification

HyperEVM read precompiles are called through `eth_call` with raw ABI arguments and no Solidity function selector:

- `0x...0801` Spot Balance
- `0x...0809` HyperCore L1 Block Number
- `0x...080f` Account Margin Summary
- `0x...0810` Core User Exists

Precompile verification defaults to only the top 3 watched wallets every 5 minutes to avoid competing heavily with the realtime EVM scanner for RPC quota.

## Recommended settings

```env
WALLET360_MIN_SCORE=60
WALLET360_MAX_WALLETS=12
WALLET360_REFRESH_SEC=60
WALLET360_VAULT_REFRESH_SEC=300
WALLET360_STATE_ALERT_USD=1000000

SMART_WALLET_STREAM_MIN_SCORE=70
SMART_WALLET_STREAM_MAX_WALLETS=8
SMART_WALLET_STREAM_REBUILD_SEC=300
SMART_WALLET_FILL_ALERT_USD=250000
SMART_WALLET_SNAPSHOT_RECOVERY_SEC=5

READ_PRECOMPILE_MAX_WALLETS=3
READ_PRECOMPILE_REFRESH_SEC=300
```

## Dashboard APIs

- `/zh`
- `/en`
- `/api/health`
- `/api/events`
- `/api/wallets`
- `/api/wallet360`
- `/api/wallet360/0x...`

## Important boundaries

- Wallet Score / P0 / P1 are engineering observation priorities, not trading recommendations.
- REST snapshots and read-precompile calls may be taken at different moments, so they are stored as dual-source verification rather than forced to match exactly.
- Smart-wallet watchlist changes use subscribe/unsubscribe on the live socket instead of scheduled disconnects.
- Unexpected reconnects accept only a short snapshot-overlap window and use persistent event dedupe; HyperCore `tid` distinguishes same-order partial fills.
- LP drain ratios remain observed priced-flow baselines, not exact TVL.
- Native HYPE Core→EVM system-transaction detection remains best-effort.
- Read-only: no private keys, seed phrases, signing or transaction submission.

## Release discipline

Stable versions should be merged into `main` only from a version branch through a pull request after the `validate` CI check and live read-only smoke pass. Repository administrators should require pull requests, require the `validate` check, and block direct pushes to `main`.
