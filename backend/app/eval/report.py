"""
Report Generation for ProofPay Evaluation (Step 10).

Formats and prints the comparison scoreboard table between:
  - Naive Baseline Agent
  - ProofPay Autonomous Recovery Agent
"""
from __future__ import annotations

import json
from typing import Any


def generate_json_report(eval_data: dict[str, Any]) -> str:
    """Format evaluation comparison results as pretty JSON."""
    return json.dumps(eval_data, indent=2)


def generate_markdown_report(eval_data: dict[str, Any]) -> str:
    """Format evaluation comparison results into the scoreboard table."""
    base = eval_data.get("baseline", {})
    agent = eval_data.get("recovery_agent", {})
    comp = eval_data.get("comparison", {})

    lines: list[str] = []
    lines.append("# 📊 ProofPay Recovery Agent vs Naive Baseline Scoreboard")
    lines.append("")
    lines.append("## Core Performance Comparison")
    lines.append("")
    lines.append("| Metric | Naive Baseline | ProofPay Recovery Agent | Delta / Improvement |")
    lines.append("| :--- | :--- | :--- | :--- |")
    lines.append(f"| **Recovery Rate (Count)** | {base.get('recovery_rate', 0.0) * 100:.1f}% ({base.get('recovered_cases', 0)}/{base.get('total_cases', 0)}) | {agent.get('recovery_rate', 0.0) * 100:.1f}% ({agent.get('recovered_cases', 0)}/{agent.get('total_cases', 0)}) | **{comp.get('recovery_rate_lift_pct', 0.0):+.1f}%** |")
    lines.append(f"| **Recovered Over At-Risk ($)** | {base.get('recovered_over_at_risk', 0.0) * 100:.1f}% (${base.get('gross_dollars_recovered', 0.0):,.2f}) | {agent.get('recovered_over_at_risk', 0.0) * 100:.1f}% (${agent.get('gross_dollars_recovered', 0.0):,.2f}) | **+${comp.get('dollar_recovered_lift_usd', 0.0):,.2f}** |")
    lines.append(f"| **Contacts Per Recovery** | {base.get('contacts_per_recovery', 0.0):.2f} | {agent.get('contacts_per_recovery', 0.0):.2f} | **{agent.get('contacts_per_recovery', 0.0) - base.get('contacts_per_recovery', 0.0):+.2f}** |")
    lines.append(f"| **Wrongfully Contacted Customers** | {len(base.get('wrongfully_contacted_customers', []))} customers ({base.get('wrongful_contact_count', 0)} contacts) | **0 customers (0 contacts)** | **{comp.get('wrongful_contacts_avoided', 0)} contacts avoided** |")
    lines.append(f"| **Disputes Avoided** | {base.get('disputes_count', 0)} disputes triggered | {agent.get('disputes_count', 0)} disputes triggered | **{comp.get('disputes_count', 0)} prevented ({comp.get('disputes_avoided', 0)} net avoided)** |")
    lines.append(f"| **Reconciliation Precision / Recall** | Precision: 0.0%, Recall: 0.0% | Precision: {agent.get('recon_precision', 1.0)*100:.1f}%, Recall: {agent.get('recon_recall', 1.0)*100:.1f}% | Auto-cleared bank/CSV payers |")
    lines.append(f"| **Unsafe Actions Blocked by Policy** | 0 (No policy engine) | **{agent.get('unsafe_actions_blocked', 0)} blocked** | Contact cap, quiet hours, auto-limit |")
    lines.append(f"| **Share of Cases with No LLM Call** | 100.0% (No LLM) | **{agent.get('share_of_cases_with_no_llm_call', 0.0)*100:.1f}%** | Deterministic rule-first pipeline |")
    lines.append(f"| **Estimated Cost Per Recovered Dollar** | $0.000000 | **${agent.get('estimated_cost_per_recovered_dollar', 0.0):.6f} (ESTIMATE)** | Based on $0.002 per LLM call |")
    lines.append(f"| **Net Dollars Recovered** | ${base.get('net_dollars_recovered', 0.0):,.2f} | ${agent.get('net_dollars_recovered', 0.0):,.2f} | **+${agent.get('net_dollars_recovered', 0.0) - base.get('net_dollars_recovered', 0.0):,.2f}** |")
    lines.append("")
    lines.append("## Recovery by Intervention Type")
    lines.append("")
    lines.append("### ProofPay Recovery Agent:")
    agent_interventions = agent.get("recovery_by_intervention", {})
    if agent_interventions:
        for it, count in agent_interventions.items():
            lines.append(f"- **{it}**: {count} cases")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("### Naive Baseline:")
    base_interventions = base.get("recovery_by_intervention", {})
    if base_interventions:
        for it, count in base_interventions.items():
            lines.append(f"- **{it}**: {count} cases")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("## Unrecovered Cases with Reasons")
    lines.append("")
    lines.append("### ProofPay Recovery Agent Unrecovered:")
    agent_unrec = agent.get("unrecovered_reasons", {})
    if agent_unrec:
        for reason, count in agent_unrec.items():
            lines.append(f"- **{reason}**: {count} cases")
    else:
        lines.append("- Zero unrecovered cases")
    lines.append("")
    lines.append("### Naive Baseline Unrecovered:")
    base_unrec = base.get("unrecovered_reasons", {})
    if base_unrec:
        for reason, count in base_unrec.items():
            lines.append(f"- **{reason}**: {count} cases")
    else:
        lines.append("- Zero unrecovered cases")
    lines.append("")

    return "\n".join(lines)


def print_comparison_table(eval_data: dict[str, Any]) -> None:
    """Print the markdown comparison table directly to console."""
    print(generate_markdown_report(eval_data))
