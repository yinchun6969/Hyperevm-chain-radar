# HyperEVM Chain Radar V0.2.0

## HYPE Smart-Money Radar

V0.2.0 connects HyperCore spot trading activity with HyperEVM capital deployment.

### Added
- HyperCore HYPE (`@107`) large-trade ingestion with buyer/seller wallets.
- Persistent smart-money wallet profiles and scores.
- Core→EVM→BUY→LP P0/P1 sequence detection.
- Full HyperSwap V3 indexed pool bootstrap via Etherscan API V2 when configured.
- Rate-conscious recent RPC bootstrap fallback.
- `/api/wallets` and upgraded bilingual dashboard.
- V0.2 reliability regression tests.

### Changed
- HyperSwap swaps and LP events now prefer transaction `from` for wallet attribution.
- Token focus for base-token pairs follows the non-USDC/non-WHYPE side.
- Doctor reports V0.2 bootstrap state and wallet database readiness.

### Safety
- Read-only monitoring only; no private keys or signing.
- Smart-money scores are heuristics.
- LP drain ratios are observed-flow estimates, not exact TVL.
