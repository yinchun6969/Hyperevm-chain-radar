# HyperEVM Chain Radar V0.2.0

HyperEVM + HyperCore 双层 HYPE 资金雷达。

## V0.2.0 核心升级

这一版不再只看 EVM 链上的 Swap/LP，而是把 HyperCore 和 HyperEVM 同一地址的行为串起来：

**HyperCore 大额成交 → Core→EVM 资金转入 → HyperSwap BUY → LP ADD → 地址评分 → P0/P1 资金链告警。**

新增：

- HyperCore HYPE Spot `@107` 实时 trades，直接读取 buyer / seller 钱包。
- Smart Money 地址画像：Core 买卖、Core→EVM、EVM 买卖、LP 加撤、资金链次数、综合分。
- `Core → EVM → BUY → LP` 同地址、同 Token 关联。
- HyperSwap V3 历史池 Bootstrap：配置 Etherscan API Key 时读取 Chain ID 999 的完整索引日志。
- 无 API Key 时使用最近区块 RPC 回退，并严格使用不超过 50 block 的日志窗口，避免滥打官方 RPC。
- Swap/LP 地址优先使用交易 `tx.from`，降低 Router 被错误当成聪明钱地址的问题。
- Dashboard 增加聪明钱排行和 `/api/wallets`。
- Doctor V0.2 增加 Pool Bootstrap / Wallet Schema 检查。

## 推荐配置

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

`ETHERSCAN_API_KEY` 不是运行必需项，但建议配置。没有 Key 时，系统不会从 Factory 部署块一路用官方 RPC 扫到最新高度，而只扫描最近的可配置窗口，这是为了控制 HyperEVM 官方 RPC 请求量。

## 风险边界

- P0/P1 和 Smart Money Score 是工程观察优先级，不是买入建议。
- LP 撤出比例是 Radar 已观察并能定价的 LP 资金流基线，不是精确 TVL。
- HyperCore→HyperEVM 原生 HYPE 系统交易仍标注 best-effort。
- 项目只读，不需要私钥、助记词或交易签名。
