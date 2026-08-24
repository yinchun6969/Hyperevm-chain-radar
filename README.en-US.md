# HyperEVM Chain Radar V0.2.0

V0.2.0 adds a HyperCore-aware smart-money layer on top of the HyperEVM scanner.

## Highlights

- HyperCore HYPE spot `@107` trade stream with buyer/seller wallet attribution.
- Wallet profiles for Core buy/sell, Core→EVM, EVM buy/sell, LP flow and capital-sequence counts.
- Same-wallet, same-token `Core → EVM → BUY → LP` correlation with P0/P1 alerts.
- HyperSwap V3 historical pool bootstrap through Etherscan API V2 (`chainid=999`) when an API key is configured.
- Recent <=50-block RPC bootstrap fallback when no indexer key is available.
- Transaction-sender attribution for HyperSwap activity to avoid treating routers as smart-money wallets.
- `/api/wallets` and smart-money dashboard table.

## Recommended settings

```env
HYPERCORE_TRADE_COINS=@107
HYPERCORE_SMART_MONEY_MIN_USD=100000
HYPERCORE_WHALE_TRADE_USD=500000
ETHERSCAN_API_KEY=
CAPITAL_SEQUENCE_WINDOW_MIN=180
CAPITAL_SEQUENCE_P1_USD=100000
CAPITAL_SEQUENCE_P0_TRANSFER_USD=500000
CAPITAL_SEQUENCE_P0_BUY_USD=250000
CAPITAL_SEQUENCE_P0_LP_USD=250000
```

## Important boundaries

Wallet scores are monitoring heuristics, not trading advice. LP drain ratios are based on observable priced flows rather than exact pool TVL. Native HYPE Core→EVM system transaction detection remains best-effort in this release.
