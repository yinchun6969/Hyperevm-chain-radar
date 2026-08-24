# HyperEVM Chain Radar V0.3.9

HyperEVM + HyperCore 双层 HYPE 资金雷达。V0.3.9 是当前 0.3.x 线的**稳定硬化版**，保留已经验收通过的 Wallet 360 逻辑，不额外改变信号语义。

## V0.3.9 稳定线

核心资金链保持：

**HyperCore 大额成交 → Core→EVM → HyperSwap BUY → LP ADD → 地址评分 → HyperCore Spot/Perp/Vault 状态 → Read Precompile 校验 → 高分钱包持续监控。**

本版主要做发布硬化：

- 版本号统一由 `core/version.py` 管理，避免 Doctor / Supervisor 显示不一致。
- CI 继续执行全仓 Python 编译、全部单元回归、真实 HyperEVM/HyperCore 只读 Smoke Test、Shell 语法检查。
- 增加公开配置发布守卫，要求示例配置不包含 Telegram Token、Chat ID 或 Etherscan Key，Dashboard 默认保持 `127.0.0.1`。
- 明确稳定版必须通过版本分支 → PR → CI → main 的发布流程。

## Wallet 360

高分钱包会持续观察：

- `clearinghouseState`：账户价值、Perp 名义仓位、保证金、可提现、未实现盈亏、最大仓位。
- `spotClearinghouseState`：HYPE / USDC 和其他 Spot 余额。
- `userVaultEquities`：Vault 资金。
- HyperEVM Read Precompile 双源状态校验。
- 高分钱包 `userFills` / `userNonFundingLedgerUpdates` 动态 WebSocket 订阅。
- 大额 Perp 名义仓位变化 P1 提醒。
- Dashboard Wallet 360 表格和 `/api/wallet360`。

## Read Precompile

使用 HyperEVM 原生 Read Precompile，调用方式是 `eth_call` + 原始 ABI 参数，不带 Solidity 函数 selector：

- `0x...0801` Spot Balance
- `0x...0809` HyperCore L1 Block Number
- `0x...080f` Account Margin Summary
- `0x...0810` Core User Exists

默认只对排名最高的 3 个观察钱包每 5 分钟校验一次，避免与实时 EVM Scanner 争抢 RPC 请求额度。

## 推荐配置

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

## Dashboard

- `/zh` 中文
- `/en` English
- `/api/health`
- `/api/events`
- `/api/wallets`
- `/api/wallet360`
- `/api/wallet360/0x...`

## 数据语义和风险边界

- Wallet Score / P0 / P1 都是工程观察优先级，不是买入建议。
- REST 快照和 Read Precompile 可能来自不同时间点，因此记录为双源校验，不强制数值完全相等。
- Smart Wallet 观察名单在现有 WebSocket 上直接 subscribe/unsubscribe，不会为了定时刷新主动断线。
- 意外重连时只接受短时间 Snapshot 重叠窗口，并通过持久化事件去重；`tid` 用于区分同一订单的多次 partial fill。
- LP 撤出比例仍是 Radar 已观察、且可美元估值的资金流基线，不是精确 TVL。
- HyperCore→HyperEVM 原生 HYPE 系统交易仍标记 best-effort。
- 项目完全只读，不需要私钥、助记词或交易签名。

## 发布纪律

稳定版本应从版本开发分支经过 Pull Request、`validate` CI 与只读 Live Smoke 后合并到 `main`。仓库管理员应对 `main` 开启：必须 PR、必须 CI、禁止直接 Push。
