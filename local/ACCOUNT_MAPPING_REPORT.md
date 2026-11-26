# TCEX 20 Accounts — Mandatory Account Mapping & Verification Report

## 1. Overview

This document presents the authoritative mapping and verification of the 20 provisioned TCEX accounts (ACC-01 through ACC-20) managing 100 strategies for the **BTC/VND** spot market.

- **Venue**: TCEX Spot Simulation (`simulation.the20.sg`)
- **Session Key**: `dc1tpbu76rkff8gccfug` (Room 285)
- **Trading Pair**: `BTC_VND` (Quote: `VND`, Base: `BTC`)
- **Total Initial Capital**: 3,000,000,000.00 VND (150,000,000.00 VND per account)
- **Total Strategy Deployable Budget**: 1,800,000,000.00 VND (90,000,000.00 VND per account)
- **Total Reserve**: 1,200,000,000.00 VND (60,000,000.00 VND per account)
- **Security Assurance**: All API keys and secret keys are securely referenced; no cleartext credentials are exposed in this document.

---

## 2. Account Identity, Balance & Verification Table

| Internal ID | Nickname | Label | Masked Username | Scope | Actual VND | Actual BTC | Connection | Reconciliation | Verification Status |
|:---|:---|:---|:---|:---:|---:|---:|:---:|:---:|:---:|
| **ACC-01** | Mu #1 | mu_acc #1 | `tmp_dc34h****qbvg` | global | 150,000,000.00 | 0.00 | CONNECTED | MATCHED | **VERIFIED** |
| **ACC-02** | Mu #2 | mu_acc #2 | `tmp_dc34h****qc00` | global | 150,000,000.00 | 0.00 | CONNECTED | MATCHED | **VERIFIED** |
| **ACC-03** | Mu #3 | mu_acc #3 | `tmp_dc34h****qc0g` | global | 150,000,000.00 | 0.00 | CONNECTED | MATCHED | **VERIFIED** |
| **ACC-04** | Mu #4 | mu_acc #4 | `tmp_dc34h****qc10` | global | 150,000,000.00 | 0.00 | CONNECTED | MATCHED | **VERIFIED** |
| **ACC-05** | Mu #5 | mu_acc #5 | `tmp_dc34h****qc1g` | global | 150,000,000.00 | 0.00 | CONNECTED | MATCHED | **VERIFIED** |
| **ACC-06** | Mu #6 | mu_acc #6 | `tmp_dc34h****qc20` | global | 150,000,000.00 | 0.00 | CONNECTED | MATCHED | **VERIFIED** |
| **ACC-07** | Mu #7 | mu_acc #7 | `tmp_dc34h****qc2g` | global | 150,000,000.00 | 0.00 | CONNECTED | MATCHED | **VERIFIED** |
| **ACC-08** | Mu #8 | mu_acc #8 | `tmp_dc34h****qc30` | global | 150,000,000.00 | 0.00 | CONNECTED | MATCHED | **VERIFIED** |
| **ACC-09** | Mu #9 | mu_acc #9 | `tmp_dc34h****qc3g` | global | 150,000,000.00 | 0.00 | CONNECTED | MATCHED | **VERIFIED** |
| **ACC-10** | Mu #10 | mu_acc #10 | `tmp_dc34h****qc40` | global | 150,000,000.00 | 0.00 | CONNECTED | MATCHED | **VERIFIED** |
| **ACC-11** | Mu #11 | mu_acc #11 | `tmp_dc34h****qc4g` | global | 150,000,000.00 | 0.00 | CONNECTED | MATCHED | **VERIFIED** |
| **ACC-12** | Mu #12 | mu_acc #12 | `tmp_dc34h****qc50` | global | 150,000,000.00 | 0.00 | CONNECTED | MATCHED | **VERIFIED** |
| **ACC-13** | Mu #13 | mu_acc #13 | `tmp_dc34h****qc5g` | global | 150,000,000.00 | 0.00 | CONNECTED | MATCHED | **VERIFIED** |
| **ACC-14** | Mu #14 | mu_acc #14 | `tmp_dc34h****qc60` | global | 150,000,000.00 | 0.00 | CONNECTED | MATCHED | **VERIFIED** |
| **ACC-15** | Mu #15 | mu_acc #15 | `tmp_dc34h****qc6g` | global | 150,000,000.00 | 0.00 | CONNECTED | MATCHED | **VERIFIED** |
| **ACC-16** | Mu #16 | mu_acc #16 | `tmp_dc34h****qc70` | global | 150,000,000.00 | 0.00 | CONNECTED | MATCHED | **VERIFIED** |
| **ACC-17** | Mu #17 | mu_acc #17 | `tmp_dc34h****qc7g` | global | 150,000,000.00 | 0.00 | CONNECTED | MATCHED | **VERIFIED** |
| **ACC-18** | Mu #18 | mu_acc #18 | `tmp_dc34h****qc80` | global | 150,000,000.00 | 0.00 | CONNECTED | MATCHED | **VERIFIED** |
| **ACC-19** | Mu #19 | mu_acc #19 | `tmp_dc34h****qc8g` | global | 150,000,000.00 | 0.00 | CONNECTED | MATCHED | **VERIFIED** |
| **ACC-20** | Mu #20 | mu_acc #20 | `tmp_dc34h****qc90` | global | 150,000,000.00 | 0.00 | CONNECTED | MATCHED | **VERIFIED** |

---

## 3. Account-to-Strategy Allocation Mapping

| Account | Assigned Strategies | Alpha Count | Live Sleeve Budget (VND) | Benchmark Strategy | Benchmark Capital | Total Live Budget | Account Reserve |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **ACC-01** | STR-001, STR-037, STR-053, STR-069, STR-085, STR-091 | 5 | 18,000,000 / strat | STR-091 | 0 VND (Paper) | 90,000,000 | 60,000,000 |
| **ACC-02** | STR-002, STR-038, STR-054, STR-070, STR-086, STR-092 | 5 | 18,000,000 / strat | STR-092 | 0 VND (Paper) | 90,000,000 | 60,000,000 |
| **ACC-03** | STR-003, STR-039, STR-055, STR-071, STR-087, STR-093 | 5 | 18,000,000 / strat | STR-093 | 0 VND (Paper) | 90,000,000 | 60,000,000 |
| **ACC-04** | STR-004, STR-040, STR-056, STR-072, STR-088, STR-094 | 5 | 18,000,000 / strat | STR-094 | 0 VND (Paper) | 90,000,000 | 60,000,000 |
| **ACC-05** | STR-005, STR-021, STR-057, STR-073, STR-089, STR-095 | 5 | 18,000,000 / strat | STR-095 | 0 VND (Paper) | 90,000,000 | 60,000,000 |
| **ACC-06** | STR-006, STR-022, STR-058, STR-074, STR-090, STR-096 | 5 | 18,000,000 / strat | STR-096 | 0 VND (Paper) | 90,000,000 | 60,000,000 |
| **ACC-07** | STR-007, STR-023, STR-059, STR-075, STR-097 | 4 | 22,500,000 / strat | STR-097 | 0 VND (Paper) | 90,000,000 | 60,000,000 |
| **ACC-08** | STR-008, STR-024, STR-060, STR-076, STR-098 | 4 | 22,500,000 / strat | STR-098 | 0 VND (Paper) | 90,000,000 | 60,000,000 |
| **ACC-09** | STR-009, STR-025, STR-041, STR-077, STR-099 | 4 | 22,500,000 / strat | STR-099 | 0 VND (Paper) | 90,000,000 | 60,000,000 |
| **ACC-10** | STR-010, STR-026, STR-042, STR-078, STR-100 | 4 | 22,500,000 / strat | STR-100 | 0 VND (Paper) | 90,000,000 | 60,000,000 |
| **ACC-11** | STR-011, STR-027, STR-043, STR-079 | 4 | 22,500,000 / strat | None | - | 90,000,000 | 60,000,000 |
| **ACC-12** | STR-012, STR-028, STR-044, STR-080 | 4 | 22,500,000 / strat | None | - | 90,000,000 | 60,000,000 |
| **ACC-13** | STR-013, STR-029, STR-045, STR-061 | 4 | 22,500,000 / strat | None | - | 90,000,000 | 60,000,000 |
| **ACC-14** | STR-014, STR-030, STR-046, STR-062 | 4 | 22,500,000 / strat | None | - | 90,000,000 | 60,000,000 |
| **ACC-15** | STR-015, STR-031, STR-047, STR-063 | 4 | 22,500,000 / strat | None | - | 90,000,000 | 60,000,000 |
| **ACC-16** | STR-016, STR-032, STR-048, STR-064 | 4 | 22,500,000 / strat | None | - | 90,000,000 | 60,000,000 |
| **ACC-17** | STR-017, STR-033, STR-049, STR-065, STR-081 | 5 | 18,000,000 / strat | None | - | 90,000,000 | 60,000,000 |
| **ACC-18** | STR-018, STR-034, STR-050, STR-066, STR-082 | 5 | 18,000,000 / strat | None | - | 90,000,000 | 60,000,000 |
| **ACC-19** | STR-019, STR-035, STR-051, STR-067, STR-083 | 5 | 18,000,000 / strat | None | - | 90,000,000 | 60,000,000 |
| **ACC-20** | STR-020, STR-036, STR-052, STR-068, STR-084 | 5 | 18,000,000 / strat | None | - | 90,000,000 | 60,000,000 |
| **TOTAL** | **100 Strategies** | **90 Alpha** | **-** | **10 Benchmarks** | **0 VND** | **1,800,000,000** | **1,200,000,000** |

---

## 4. Key Rules Enforced

1. **No Shared Wallets Double-Spending**: Multiple strategies within an account share the same wallet, but the central reservation ledger ensures that total active reservations never exceed the 90,000,000 VND deployable budget.
2. **Behavioral Strategies (STR-091 to STR-100)**: Assigned 0 live capital and restricted strictly to paper simulation.
3. **No Short Selling**: Selling requires unreserved BTC ownership in the account.
4. **LIMIT Orders Only**: Venue enforces strict LIMIT orders with price precision 2 decimals and lot precision 2 decimals (min 0.01 BTC).
