# HyperEVM Chain Radar V0.3.9 — Stable Hardening Release

V0.3.9 freezes the validated V0.3 Wallet 360 line as the final stable 0.3.x release before any future V0.4.0 feature work.

## What changed

- Centralized runtime version metadata in `core/version.py`.
- Doctor and Supervisor now read the same version source.
- Added `release_guard.py` and made it a required CI step for this release process.
- Release guard verifies:
  - public Telegram Bot Token is empty;
  - public Telegram Chat ID is empty;
  - public Etherscan API key is empty;
  - Dashboard defaults to `127.0.0.1`;
  - public RPC/Info/WebSocket defaults use HTTPS/WSS;
  - README titles and runtime version metadata agree.
- Updated bilingual documentation for V0.3.9.

## Stable monitoring capabilities

- HyperEVM Chain ID 999 realtime scanner.
- HyperCore HYPE smart-money stream.
- HyperSwap V3 pool discovery and historical bootstrap.
- Core → EVM → BUY → LP P0/P1 correlation.
- Wallet Score and Wallet 360 intelligence.
- HyperCore Spot / Perp / Vault snapshots.
- HyperEVM Read Precompile verification.
- Dynamic high-score wallet `userFills` and `userNonFundingLedgerUpdates` subscriptions.
- Gapless scheduled watchlist refresh through live subscribe/unsubscribe.
- Bounded reconnect snapshot recovery and HyperCore `tid`-safe fill dedupe.
- LP withdrawal / rug-risk radar.
- Telegram, bilingual local dashboard, Android Termux and Ubuntu systemd.
- RPC failover and Doctor diagnostics.

## Validation policy

This release must pass:

1. public release guard;
2. full Python compilation;
3. all regression tests;
4. live read-only HyperEVM / HyperCore smoke checks;
5. shell-script syntax validation;
6. pull-request review before merge to `main`.

## Security boundary

The project remains read-only. It does not require private keys or seed phrases and does not sign or submit transactions.

Wallet Score, P0/P1 priorities and LP-drain heuristics are monitoring signals, not investment advice or a smart-contract audit.
