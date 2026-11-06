"""Deterministic answers for the 'local' provider.

Builds a plain-text explanation strictly from the verified context dict, so the
assistant works (and is testable) without any external AI service.
"""
from decimal import Decimal

from app.services.ai_service import detect_intents


def _fmt(value, currency: str) -> str:
    if value is None:
        return "n/a"
    amount = Decimal(str(value))
    symbol = "৳" if currency == "BDT" else f"{currency} "
    sign = "-" if amount < 0 else ""
    return f"{sign}{symbol}{abs(amount):,.2f}"


def compose_answer(question: str, ctx: dict) -> str:
    cur = ctx.get("currency", "BDT")
    f = lambda v: _fmt(v, cur)  # noqa: E731
    intents = detect_intents(question)
    period = ctx["period"]["label"]
    t = ctx["totals"]
    p = ctx["previous_period"]
    suff = ctx["data_sufficiency"]
    lines: list[str] = []

    if suff["transactions_recorded_total"] == 0:
        return ("I don't have any of your financial records yet, so I can't answer that from real data. "
                "Add your accounts and a few income and expense transactions, then ask again and I'll "
                "explain your spending, budgets and savings.")

    if suff["transactions_in_period"] == 0:
        lines.append(f"I don't see any income or expenses recorded for {period} "
                     f"({ctx['period']['start']} to {ctx['period']['end']}).")
    else:
        rate = t["savings_rate_percent"]
        lines.append(
            f"For {period}: income {f(t['income'])}, net expenses {f(t['net_expense'])}"
            + (f" (after {f(t['refunds'])} in refunds)" if Decimal(str(t["refunds"])) > 0 else "")
            + f", net cash flow {f(t['net_cash_flow'])}."
            + (f" Your savings rate is {rate}%." if rate is not None else " Savings rate is not available because no income is recorded.")
        )
        if p["transactions"]:
            diff = Decimal(str(t["net_expense"])) - Decimal(str(p["net_expense"]))
            direction = "more" if diff > 0 else "less"
            if diff != 0:
                lines.append(f"That is {f(abs(diff))} {direction} spending than the previous period "
                             f"({f(p['net_expense'])}).")

    cats = ctx.get("expense_by_category") or []
    if cats and ("spending" in intents or "general" in intents or "advice" in intents or "trend" in intents):
        top = ", ".join(f"{c['category']} {f(c['amount'])} ({c['share_percent']}%)" for c in cats[:3])
        lines.append(f"Biggest expense categories: {top}.")
        rising = [c for c in cats if c.get("change_percent") is not None and Decimal(str(c["change_percent"])) >= 25]
        if rising:
            lines.append("Rising vs the previous period: " + ", ".join(
                f"{c['category']} (+{c['change_percent']}%)" for c in rising[:3]) + ".")

    for b in ctx.get("budgets_this_month", []) or []:
        if b["status"] == "exceeded":
            lines.append(f"• {b['budget']} budget is exceeded: {f(b['spent'])} of {f(b['limit'])}.")
        elif b["status"] == "warning":
            lines.append(f"• {b['budget']} budget is at {b['utilization_percent']}% ({f(b['remaining'])} left).")
    if "budget" in intents and not ctx.get("budgets_this_month"):
        lines.append("You haven't set any budgets for this month. Setting an overall limit is a good first step.")

    bills = ctx.get("bills")
    if bills:
        overdue = [b for b in bills["unpaid"] if b["status"] == "overdue"]
        upcoming = [b for b in bills["unpaid"] if b["status"] != "overdue"]
        if overdue:
            lines.append("Overdue bills: " + ", ".join(f"{b['title']} {f(b['amount'])} (due {b['due_date']})"
                                                       for b in overdue) + ".")
        if upcoming:
            lines.append("Upcoming bills: " + ", ".join(f"{b['title']} {f(b['amount'])} on {b['due_date']}"
                                                        for b in upcoming[:5]) + ".")
        changed = [b for b in bills["unpaid"] + bills["recently_paid"] if b.get("change_vs_previous_percent") is not None]
        for b in changed[:3]:
            lines.append(f"{b['title']} changed {b['change_vs_previous_percent']}% vs the previous {b['type']} bill.")
        if not bills["unpaid"] and not bills["recently_paid"]:
            lines.append("You have no bills recorded yet.")

    for g in ctx.get("savings_goals", []) or []:
        s = f"• Goal '{g['goal']}': {f(g['saved'])} of {f(g['target'])} ({g['progress_percent']}%)."
        if g.get("required_monthly") is not None and g["status"] == "active":
            s += f" Needs about {f(g['required_monthly'])}/month to hit {g['target_date']}."
            if g.get("on_track") is False:
                s += " Currently behind schedule."
            elif g.get("on_track"):
                s += " On track."
        lines.append(s)
    if "savings" in intents and not ctx.get("savings_goals"):
        lines.append("You don't have any savings goals yet. Create one to track progress.")

    if ctx.get("accounts"):
        lines.append("Balances: " + ", ".join(f"{a['account']} {f(a['balance'])}" for a in ctx["accounts"]) + ".")

    if "trend" in intents and ctx.get("monthly_trend_last_6_months"):
        months = [m for m in ctx["monthly_trend_last_6_months"] if Decimal(str(m["income"])) or Decimal(str(m["net_expense"]))]
        if len(months) >= 2:
            lines.append("Monthly net expenses: " + ", ".join(f"{m['month']} {f(m['net_expense'])}" for m in months) + ".")
        else:
            lines.append("There isn't enough monthly history yet to show a trend.")

    # Suggestions grounded in the figures
    tips = []
    if t["savings_rate_percent"] is not None and Decimal(str(t["savings_rate_percent"])) < 10 and cats:
        tips.append(f"Your savings rate is low. Trimming {cats[0]['category']} by 10% would free up about "
                    f"{f(Decimal(str(cats[0]['amount'])) * Decimal('0.1'))}.")
    if any(b["status"] == "exceeded" for b in ctx.get("budgets_this_month", []) or []):
        tips.append("Pause non-essential spending in the exceeded categories for the rest of the month.")
    if bills and any(b["status"] == "overdue" for b in bills["unpaid"]):
        tips.append("Pay overdue bills first to avoid late fees or disconnection.")
    if tips and ("advice" in intents or "general" in intents or "spending" in intents or "budget" in intents):
        lines.append("Suggestions:\n" + "\n".join(f"• {x}" for x in tips))

    for note in suff["notes"]:
        if "previous comparable" in note and "trend" not in intents:
            continue
        lines.append(f"Note: {note}")
    return "\n\n".join(lines)
