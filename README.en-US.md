# HyperEVM Chain Radar V0.1.0

An independent open-source capital-flow monitor for **HyperEVM + HyperCore**.

## Initial scope
- HyperEVM Chain ID `999`
- small/big dual-block classification
- HyperCore `allMids` WebSocket HYPE price feed
- Core ↔ EVM system-transfer observations
- CoreWriter action monitoring
- HyperSwap V3 new pools, swaps, LP adds/removes
- conservative USDC / WHYPE USD valuation
- P0/P1 LP withdrawal radar
- Telegram, SQLite, local dashboard and Doctor
- Android Termux and Ubuntu systemd

LP withdrawal percentages are based on priced flow observed by the radar, not exact pool TVL.

V0.1.0 begins HyperSwap V3 activity tracking when a pool is discovered via `PoolCreated`; historical pool bootstrapping is planned next.

This is read-only monitoring software. It does not require private keys or transaction signing.
