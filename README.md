# HyperEVM Chain Radar V0.2.0

**中文 | English** — HyperEVM + HyperCore capital-flow and smart-money monitoring.

[中文说明](README.zh-CN.md) · [English README](README.en-US.md)

> Independent community project. Not affiliated with or endorsed by Hyperliquid, HyperSwap, or Etherscan.

## V0.2.0 — HYPE Smart-Money Radar

V0.2.0 upgrades the V0.1 EVM scanner into a two-layer capital radar:

**HyperCore trade → Core→EVM transfer → HyperSwap BUY → LP deployment → wallet score → P0/P1 sequence alert.**

### New in V0.2.0

- HyperCore HYPE spot trade stream (`@107`) with buyer/seller wallet attribution.
- Smart-money wallet profiles: Core buys/sells, Core→EVM flows, EVM buys/sells, LP adds/removes, sequence count and score.
- `Core → EVM → BUY → LP` correlation with token matching and P0/P1 Telegram alerts.
- HyperSwap V3 historical pool bootstrap.
  - Full indexed history when `ETHERSCAN_API_KEY` is configured.
  - Recent RPC fallback without a key, using <=50-block `eth_getLogs` windows.
- Swap/LP actor attribution uses transaction sender where available, rather than router-only event sender.
- Dashboard smart-money table and `/api/wallets`.
- Doctor V0.2 checks pool bootstrap mode and wallet schema.

V0.1 capabilities remain: Chain ID 999 dual-block scan, HyperCore allMids price feed, CoreWriter monitoring, HyperSwap V3 pool/swap/LP monitoring, LP withdrawal radar, RPC failover, SQLite, Telegram, Android Termux and Ubuntu systemd.

## Quick start

```bash
# Android / Termux
pkg update
pkg install -y git
git clone https://github.com/yinchun6969/Hyperevm-chain-radar.git
cd Hyperevm-chain-radar
bash scripts/android/install-termux.sh
```

```bash
# Ubuntu
sudo bash scripts/ubuntu/install.sh
```

Dashboard: `http://127.0.0.1:8788/zh` · `/en`  
APIs: `/api/health` · `/api/events` · `/api/wallets`

## Recommended V0.2 config

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

## Important semantics

- HyperCore `trades` exposes buyer/seller users; V0.2 uses this for wallet-level Core activity.
- HYPE spot on HyperCore mainnet is tracked as `@107` by default.
- Full HyperSwap pool history uses Etherscan API V2 with `chainid=999`; official HyperEVM JSON-RPC remains the realtime source.
- Without an Etherscan key, bootstrap intentionally scans only a recent configurable RPC window to avoid hundreds of thousands of requests.
- HyperCore→HyperEVM native HYPE system-transaction detection remains best-effort.
- LP withdrawal percentages are Radar-observed priced-flow baselines, not exact TVL.
- Wallet scores are engineering observation scores, not investment recommendations.

## Verified network constants

- HyperEVM Chain ID: `999`
- RPC: `https://rpc.hyperliquid.xyz/evm`
- HYPE system: `0x2222222222222222222222222222222222222222`
- CoreWriter: `0x3333333333333333333333333333333333333333`
- WHYPE: `0x5555555555555555555555555555555555555555`
- HyperSwap V3 Factory: `0xB1c0fa0B789320044A6F623cFe5eBda9562602E3`
- HyperSwap V3 Factory deployment block used for indexed bootstrap: `11648`

## License
MIT
