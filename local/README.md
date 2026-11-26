# TCEX BTC/VND Multi-Account Strategy Engine

Autonomous multi-account algorithmic trading system designed to operate and manage 100 strategies across 20 accounts on the TCEX simulation venue (`simulation.the20.sg`), strictly dedicated to the **BTC/VND** Spot market.

---

## 1. Architectural Highlights

- **Venue & Market**: TCEX Spot Simulation (`simulation.the20.sg`).
- **Session Key**: `dc1tpbu76rkff8gccfug` (Room 285).
- **Trading Pair**: `BTC_VND` (Quote: `VND`, Base: `BTC`).
- **Order Type**: **Strict LIMIT only**. No market orders, no margin, no leverage, no short selling.
- **Precision**: Price scale = 2 decimals (step 0.01 VND), Qty scale = 2 decimals (min 0.01 BTC).
- **Capital Structure**:
  - 20 Accounts (ACC-01 through ACC-20).
  - 150,000,000 VND initial capital per account (Total: 3,000,000,000 VND).
  - 90,000,000 VND strategy deployable budget per account (Total: 1,800,000,000 VND).
  - 60,000,000 VND reserve per account (Total: 1,200,000,000 VND).
  - Individual strategy sleeves: 18,000,000 VND (accounts with 5 alpha strategies) or 22,500,000 VND (accounts with 4 alpha strategies).
  - Behavioral strategies STR-091 through STR-100: **Paper simulation only, live capital = 0 VND**.

---

## 2. Directory Structure

```
simulate-sdk/
├── main.py                                      # Central application entry point
├── config.json                                  # Centralized system, account, strategy & risk configuration
├── requirements.txt                             # Python package dependencies
├── .env.example                                 # Environment variable template
├── credential_template.env                      # Account-specific credential template without leaking secrets
├── account_mapping.json                         # Account identity mapping
├── account_status.json                          # Live connection & balance status
├── account_strategy_mapping.json               # Account-to-strategy assignment mapping
├── ACCOUNT_MAPPING_REPORT.md                    # Account verification and mapping report
├── IMPLEMENTATION_REPORT.md                     # Comprehensive technical implementation report
├── README.md                                    # This operations manual
│
├── exchange/
│   ├── tcex_adapter.py                         # TCEX Spot adapter for BTC/VND execution
│   └── market_data.py                          # Market Data Manager (Ticker, Orderbook, Klines, Indicators)
│
├── storage/
│   ├── models.py                               # Database entity models
│   └── database.py                             # SQLite thread-safe persistence layer
│
├── engine/
│   ├── account_manager.py                      # 20 accounts manager & read-only verification
│   ├── capital_manager.py                      # Central reservation ledger & sleeve budget enforcement
│   ├── portfolio_manager.py                    # Multi-account balances, positions & live PnL in VND
│   ├── risk_manager.py                         # Multi-tier risk engine, duplicate prevention & isolation
│   ├── execution_engine.py                     # Execution orchestrator (PAPER fill matching & LIVE routing)
│   └── strategy_manager.py                     # 100 strategy runner with error containment
│
├── monitoring/
│   ├── logger.py                               # Masked logging & structured audit trails
│   ├── metrics.py                              # Realized/unrealized PnL, win rates, drawdowns
│   └── health.py                               # Subsystem heartbeats & error isolation
│
├── strategies/
│   ├── __init__.py                             # Strategy registry & factory
│   ├── base.py                                 # BaseStrategy class with LIMIT signal generation
│   ├── indicators.py                           # Technical indicators (SMA, EMA, RSI, MACD, ATR, BB, VWAP)
│   ├── grid_dca.py                             # STR-001 - STR-010 (Grid & DCA family)
│   ├── mean_reversion.py                       # STR-011 - STR-020 (Mean Reversion family)
│   ├── trend_following.py                      # STR-021 - STR-030 (Trend Following family)
│   ├── momentum.py                             # STR-031 - STR-040 (Momentum family)
│   ├── breakout.py                             # STR-041 - STR-050 (Breakout family)
│   ├── scalping.py                             # STR-051 - STR-060 (Scalping family)
│   ├── order_flow.py                           # STR-061 - STR-070 (Order Flow family)
│   ├── cross_arbitrage.py                      # STR-071 - STR-080 (Cross-Exchange Arbitrage family)
│   ├── news_event.py                           # STR-081 - STR-090 (News / Event family)
│   └── behavioral.py                           # STR-091 - STR-100 (Behavioral benchmark family - paper only)
│
└── tests/
    ├── test_config.py                          # Config schema and capital math tests
    ├── test_accounts.py                        # Account mapping and verification tests
    ├── test_capital.py                         # Central reservation and sleeve tests
    ├── test_strategies.py                      # 100 strategy registrations and family tests
    ├── test_risk.py                            # LIMIT-only, stale data, duplicate order tests
    ├── test_execution.py                       # Paper orderbook matching and fill tests
    └── run_all_tests.py                        # Master automated test runner
```

---

## 3. Quick Start

### Installation

```bash
cd E:\My\the20\simulate-sdk
pip install -r requirements.txt
```

### Run Automated Tests

To verify that all 24 automated unit and integration tests pass:
```bash
python tests/run_all_tests.py
```

### Run System in PAPER Mode (Default)

To run the engine continuously in PAPER mode:
```bash
python main.py
```

To run a verification-only dry run (verifies all 20 accounts and market, then exits):
```bash
python main.py --verify-only
```

To run for a specific number of evaluation ticks (e.g. 10 ticks):
```bash
python main.py --iterations 10 --interval 2.0
```

### Run System in LIVE Mode

LIVE execution is strictly gated by operator confirmation. To enable LIVE execution:
```bash
python main.py --mode LIVE --confirm-live
```
*(If `--confirm-live` is not supplied, the engine will safely reject live execution and default back to PAPER mode).*

---

## 4. Logging & Monitoring Control

Hệ thống ghi log tự động theo 3 luồng chuyên biệt trong thư mục `logs/`:

| Log File | Mục đích | Nội dung |
|---|---|---|
| [`logs/tcex_engine.log`](file:///e:/My/the20/simulate-sdk/local/logs/tcex_engine.log) | Master Engine Log | Toàn bộ sự kiện hệ thống, 20 bước khởi động, heartbeat, tín hiệu chiến lược, snapshot danh mục |
| [`logs/orders.log`](file:///e:/My/the20/simulate-sdk/local/logs/orders.log) | Orders & Fills Log | Đặt lệnh (`SUBMITTED`), khớp lệnh (`FILLED`), hủy (`CANCELED`), từ chối (`REJECTED`) theo từng Account/Strategy |
| [`logs/audit_events.log`](file:///e:/My/the20/simulate-sdk/local/logs/audit_events.log) | Risk Audit Log | Vi phạm rủi ro, chặn lệnh trùng, ngắt khẩn cấp (`EMERGENCY_STOP`), cảnh báo bảo mật |

### Các lệnh xem và theo dõi log (CLI Log Viewer):

```bash
# Xem 30 dòng log hệ thống gần nhất
python view_logs.py

# Theo dõi trực tiếp (live stream tail -f) log hệ thống
python view_logs.py -f

# Xem riêng lịch sử lệnh đặt và khớp lệnh
python view_logs.py --orders

# Theo dõi trực tiếp các lệnh giao dịch phát sinh trong thời gian thực
python view_logs.py --orders -f

# Xem các sự kiện vi phạm hạn mức rủi ro / kiểm toán
python view_logs.py --audit

# Lọc log theo tài khoản hoặc chiến lược cụ thể
python view_logs.py --account ACC-01
python view_logs.py --strategy STR-001

# Kiểm tra dung lượng và trạng thái các file log
python view_logs.py --status
```

---

## 5. Multi-Tier Risk Protection

1. **Central Reservation Ledger**: Buy orders pre-reserve VND against the account's 90,000,000 VND deployable budget and strategy sleeve limit. Sell orders pre-reserve BTC against unreserved ownership. No strategy can double-spend or sell unowned coins.
2. **Strict LIMIT-Only**: Any non-LIMIT order is blocked immediately by the Risk Manager and rejected at the adapter level.
3. **No Short Selling**: Sell orders require verified physical BTC balance.
4. **Stale Data Protection**: Market data older than 30 seconds triggers an automatic order submission freeze.
5. **Duplicate Order Prevention**: Hashing order attributes within a rolling 3-second window prevents duplicate rapid-fire orders.
6. **Subsystem Isolation**: A fatal error in one strategy is isolated by the HealthMonitor and will never crash the main application loop or other accounts.
