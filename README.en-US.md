# HyperEVM Chain Radar V0.3.0

V0.3.0 adds **Wallet 360 Intelligence** to the HyperCore-aware smart-money radar.

## What V0.3.0 adds

V0.2 already correlates:

**HyperCore trade → Core→EVM → HyperSwap BUY → LP ADD → wallet score → P0/P1 sequence alert.**

V0.3.0 enriches the highest-scoring wallets with HyperCore account state:

- `clearinghouseState`: account value, perp notional, margin used, withdrawable amount, unrealized PnL and largest open position.
- `spotClearinghouseState`: HYPE / USDC and other spot balances.
- `userVaultEquities`: observed vault equity.
- HyperEVM Read Precompile verification for the same wallet.
- Dynamic `userFills` and `userNonFundingLedgerUpdates` WebSocket subscriptions for high-score wallets.
- P1 alert for large changes in observed perp notional exposure.
- Wallet 360 dashboard and `/api/wallet360` endpoints.

## Read Precompile verification

HyperEVM read precompiles are called through `eth_call` with raw ABI arguments and no Solidity function selector.

V0.3.0 uses:

- `0x...0801` Spot Balance
- `0x...0809` HyperCore L1 Block Number
- `0x...080f` Account Margin Summary
- `0x...0810` Core User Exists

To avoid competing with the realtime EVM scanner for RPC quota, precompile verification defaults to the top 3 watched wallets every 5 minutes.

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

READ_PRECOMPILE_MAX_WALLETS=3
READ_PRECOMPILE_REFRESH_SEC=300
```

Only wallets that have already reached the configured smart-money score are queried by the Wallet 360 service.

## Dashboard APIs

- `/zh`
- `/en`
- `/api/health`
- `/api/events`
- `/api/wallets`
- `/api/wallet360`
- `/api/wallet360/0x...`

Wallet 360 exposes the wallet score, HyperCore account value, perp notional and unrealized PnL, largest perp position, HYPE/USDC spot balances, vault equity and read-precompile status.

## Important boundaries

- Wallet Score / P0 / P1 are engineering observation priorities, not trading recommendations.
- REST snapshots and read-precompile calls may be taken at different moments, so they are stored as dual-source verification rather than forced to match exactly.
- `isSnapshot=true` user WebSocket messages are ignored after reconnect to prevent historical fill replay.
- LP drain ratios remain observed priced-flow baselines, not exact TVL.
- Native HYPE Core→EVM system transaction detection remains best-effort.
- Read-only: no private keys, seed phrases, signing or transaction submission.
