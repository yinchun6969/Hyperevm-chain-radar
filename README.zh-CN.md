# HyperEVM Chain Radar V0.3.0

HyperEVM + HyperCore 双层 HYPE 资金雷达，V0.3.0 新增 **Wallet 360 Intelligence**。

## V0.3.0 核心升级

V0.2 已经可以把：

**HyperCore 大额成交 → Core→EVM → HyperSwap BUY → LP ADD → 地址评分 → P0/P1 资金链告警**

串起来。

V0.3.0 再增加高分钱包的 HyperCore 状态：

- `clearinghouseState`：账户价值、Perp 名义仓位、保证金、可提现、未实现盈亏、最大仓位。
- `spotClearinghouseState`：HYPE / USDC 和其他 Spot 余额。
- `userVaultEquities`：Vault 资金。
- HyperEVM Read Precompile 同块状态校验。
- 高分钱包 `userFills` / `userNonFundingLedgerUpdates` 动态 WebSocket 订阅。
- 大额 Perp 名义仓位变化 P1 提醒。
- Dashboard 新增 Wallet 360 表格和 `/api/wallet360`。

## Read Precompile

V0.3.0 使用 HyperEVM 原生 Read Precompile，调用方式是 `eth_call` + 原始 ABI 参数，不带 Solidity 函数 selector：

- `0x...0801` Spot Balance
- `0x...0809` HyperCore L1 Block Number
- `0x...080f` Account Margin Summary
- `0x...0810` Core User Exists

默认只对排名最高的 3 个观察钱包每 5 分钟校验一次，避免与 1 秒级 HyperEVM Scanner 争抢 RPC 请求额度。

## 默认观察策略

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

这意味着普通低分地址不会不断调用 HyperCore 用户状态接口。只有已经通过 Core/EVM/Swap/LP 行为进入高分区的钱包才会进入 Wallet 360。

## Dashboard

- `/zh` 中文
- `/en` English
- `/api/health`
- `/api/events`
- `/api/wallets`
- `/api/wallet360`
- `/api/wallet360/0x...`

Wallet 360 会展示：

- Wallet Score
- HyperCore Account Value
- Perp Notional
- Unrealized PnL
- 最大 Perp 仓位
- HYPE / USDC Spot
- Vault Equity
- Read Precompile 是否成功

## 数据语义和风险边界

- Wallet Score / P0 / P1 都是工程观察优先级，不是买入建议。
- REST 快照和 Read Precompile 可能来自不同时间点，因此记录为双源校验，不强制数值完全相等。
- Smart Wallet WebSocket 连接/重建时会忽略 `isSnapshot=true` 的历史数据，避免重启后补发旧成交。
- LP 撤出比例仍是 Radar 已观察、且可美元估值的资金流基线，不是精确 TVL。
- HyperCore→HyperEVM 原生 HYPE 系统交易仍标记 best-effort。
- 项目完全只读，不需要私钥、助记词或交易签名。
