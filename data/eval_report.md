# 📊 ProofPay Recovery Agent vs Naive Baseline Scoreboard

## Core Performance Comparison

| Metric | Naive Baseline | ProofPay Recovery Agent | Delta / Improvement |
| :--- | :--- | :--- | :--- |
| **Recovery Rate (Count)** | 8.0% (12/150) | 28.7% (43/150) | **+20.7%** |
| **Recovered Over At-Risk ($)** | 6.8% ($2,560.65) | 29.2% ($11,010.00) | **+$8,449.35** |
| **Contacts Per Recovery** | 27.08 | 0.84 | **-26.24** |
| **Wrongfully Contacted Customers** | 23 customers (81 contacts) | **0 customers (0 contacts)** | **81 contacts avoided** |
| **Disputes Avoided** | 71 disputes triggered | 8 disputes triggered | **0 prevented (63 net avoided)** |
| **Reconciliation Precision / Recall** | Precision: 0.0%, Recall: 0.0% | Precision: 100.0%, Recall: 100.0% | Auto-cleared bank/CSV payers |
| **Unsafe Actions Blocked by Policy** | 0 (No policy engine) | **61 blocked** | Contact cap, quiet hours, auto-limit |
| **Share of Cases with No LLM Call** | 100.0% (No LLM) | **100.0%** | Deterministic rule-first pipeline |
| **Estimated Cost Per Recovered Dollar** | $0.000000 | **$0.000000 (ESTIMATE)** | Based on $0.002 per LLM call |
| **Net Dollars Recovered** | $2,560.65 | $11,010.00 | **+$8,449.35** |

## Recovery by Intervention Type

### ProofPay Recovery Agent:
- **reconciliation_auto_match**: 39 cases
- **send_email**: 4 cases

### Naive Baseline:
- **send_reminder**: 12 cases

## Unrecovered Cases with Reasons

### ProofPay Recovery Agent Unrecovered:
- **Needs approval: ['over_auto_limit']**: 48 cases
- **awaiting_customer_response**: 38 cases
- **customer_dispute**: 8 cases
- **diagnosed_as_insufficient_funds**: 3 cases
- **diagnosed_as_temporary_hold**: 2 cases
- **policy_denied_['daily_cap_reached']**: 5 cases
- **policy_denied_['over_auto_limit', 'daily_cap_reached']**: 3 cases

### Naive Baseline Unrecovered:
- **max_attempts_reached**: 67 cases
- **customer_dispute**: 71 cases
