# HyperEVM Chain Radar V0.1.0

面向 **HyperEVM + HyperCore** 的独立开源资金监控项目。

## 第一版重点

- Chain ID `999` HyperEVM 实时扫描
- small / big 双区块识别
- HyperCore `allMids` WebSocket HYPE 价格
- HYPE / HIP-1 资产 Core ↔ EVM 系统转账识别
- CoreWriter Action ID 监控
- HyperSwap V3 新池、Swap、Add LP、Remove LP
- USDC / WHYPE 保守美元估值
- LP 大额撤出 P0/P1
- Telegram、SQLite、本地 Dashboard、Doctor
- Android Termux / Ubuntu systemd

`LP_RUG_P0_DRAIN_PCT` 使用 Radar 已观察且能完成美元估值的 LP 流量基线，不等于精确 TVL 跌幅。

V0.1.0 从 `PoolCreated` 发现 HyperSwap V3 新池后开始跟踪；历史已有池 bootstrap 放到下一阶段。

### Android
```bash
pkg update
pkg install -y git
git clone https://github.com/yinchun6969/Hyperevm-chain-radar.git
cd Hyperevm-chain-radar
bash scripts/android/install-termux.sh
```

安装后：
```bash
cd ~/hyperevm-chain-radar
bash start-termux.sh
.venv/bin/python doctor.py
```

Dashboard：`http://127.0.0.1:8788/zh`

### Ubuntu
```bash
git clone https://github.com/yinchun6969/Hyperevm-chain-radar.git
cd Hyperevm-chain-radar
sudo bash scripts/ubuntu/install.sh
```

本项目只读监控，不需要私钥、助记词或交易签名。
