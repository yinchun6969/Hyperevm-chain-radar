#!/usr/bin/env python3
from pathlib import Path

from core.version import VERSION, VERSION_LABEL

ROOT = Path(__file__).resolve().parent
EXPECTED_VERSION = "0.3.9"


def parse_env(path: Path):
    out = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def require(condition, message):
    if not condition:
        raise SystemExit(f"RELEASE_GUARD_FAIL: {message}")


def main():
    require(VERSION == EXPECTED_VERSION, f"core version is {VERSION}, expected {EXPECTED_VERSION}")

    env = parse_env(ROOT / ".env.example")
    for key in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "ETHERSCAN_API_KEY"):
        require(env.get(key, "") == "", f"{key} must be empty in .env.example")
    require(env.get("DASHBOARD_HOST") == "127.0.0.1", "dashboard must default to loopback")
    require(env.get("HYPEREVM_RPC_URL", "").startswith("https://"), "HyperEVM RPC default must use HTTPS")
    require(env.get("HYPERCORE_INFO_URL", "").startswith("https://"), "HyperCore Info default must use HTTPS")
    require(env.get("HYPERCORE_WS_URL", "").startswith("wss://"), "HyperCore WS default must use WSS")

    for name in ("README.md", "README.zh-CN.md", "README.en-US.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        require(VERSION_LABEL in text.splitlines()[0], f"{name} title must contain {VERSION_LABEL}")

    doctor = (ROOT / "doctor.py").read_text(encoding="utf-8")
    supervisor = (ROOT / "supervisor.py").read_text(encoding="utf-8")
    require("from core.version import VERSION_LABEL" in doctor, "doctor must use centralized version")
    require("from core.version import VERSION_LABEL" in supervisor, "supervisor must use centralized version")

    print(f"RELEASE_GUARD_OK {VERSION_LABEL}")


if __name__ == "__main__":
    main()
