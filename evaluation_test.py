"""
Evaluation Test - End-to-End assessment of the whole Cash Flow Model.
=====================================================================
Runs every component of the tool against independent, hand-computed
expectations and cross-checks internal consistency:

  1. Financial invariants (balance, available cash, DSO, runway formulas)
  2. Forecast integrity (continuity, anchor, income totals, no double counting)
  3. Scenario / stress / Monte Carlo behavior (monotonicity, determinism)
  4. Loader round-trips (JSON, CSV, Excel - config incl. sales tax persisted)
  5. Output artifacts (Excel export, matplotlib dashboards, HTML dashboard)
  6. API connector integration end-to-end
  7. Honest insolvency flag (does the model say NO when it should?)

Run: python evaluation_test.py
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta

import matplotlib
matplotlib.use('Agg')

import pandas as pd

from cash_flow_model import (
    CashFlowModel, Invoice, Expense, Project,
    PaymentStatus, ExpenseType
)
from scenario_loader import ScenarioLoader
from connectors.stripe import StripeConnector
from connectors.base import ConnectorError
from dashboard import CashFlowDashboard
from generate_dashboard import generate_html_dashboard


class Evaluation:
    """Collects pass/fail checks with detail strings."""

    def __init__(self, section):
        self.section = section
        self.passed = 0
        self.failed = 0
        self.errors = []

    def check(self, name, condition, detail=""):
        if condition:
            self.passed += 1
            print(f"    [PASS] {name}")
        else:
            self.failed += 1
            self.errors.append(f"{self.section}: {name} - {detail}")
            print(f"    [FAIL] {name} - {detail}")

    def near(self, name, actual, expected, tol=0.01, detail=""):
        self.check(name, abs(actual - expected) < tol,
                   f"{detail} got {actual}, expected {expected}")


def build_full_model(sales_tax_rate: float = 0.21) -> CashFlowModel:
    """A realistic mid-size consulting firm: all data states represented."""
    now = datetime.now()
    model = CashFlowModel(initial_balance=100000)
    model.set_monthly_fixed_costs({'rent': 3000, 'salaries': 35000})
    model.set_dpo_days(28)
    model.set_dio_days(0)
    model.set_tax_rate(0.25)
    model.set_sales_tax_rate(sales_tax_rate)

    # Expenses: recurring variable, one-time, non-recurring variable
    model.add_expense(Expense('EXP-1', 'Cloud', 500, now - timedelta(days=3),
                              ExpenseType.VARIABLE, 'Infrastructure', True))
    model.add_expense(Expense('EXP-2', 'Legal', 2000, now - timedelta(days=5),
                              ExpenseType.ONE_TIME, 'Legal', False))
    model.add_expense(Expense('EXP-3', 'Subscriptions', 300, now - timedelta(days=2),
                              ExpenseType.VARIABLE, 'Software', False))

    # Invoices: received (historical), pending (future), late (aged)
    model.add_invoice(Invoice('INV-R1', 'Acme', 25000, now - timedelta(days=40),
                              now - timedelta(days=10), 30,
                              PaymentStatus.RECEIVED, now - timedelta(days=20), 25000))
    model.add_invoice(Invoice('INV-P1', 'Beta', 40000, now - timedelta(days=10),
                              now + timedelta(days=20), 30, PaymentStatus.PENDING))
    model.add_invoice(Invoice('INV-P2', 'Gamma', 30000, now - timedelta(days=10),
                              now + timedelta(days=50), 60, PaymentStatus.PENDING))
    model.add_invoice(Invoice('INV-L1', 'Omega', 10000, now - timedelta(days=80),
                              now - timedelta(days=50), 30,
                              PaymentStatus.LATE, None, 0))

    # Project with a single non-invoiced milestone (no client overlap -> no dedup)
    model.add_project(Project('PRJ-1', 'Client Z', 50000, now - timedelta(days=30),
                              now + timedelta(days=90),
                              [{'name': 'Delivery', 'amount': 50000,
                                'date': now + timedelta(days=60), 'paid': False}],
                              0, 20))
    return model


def evaluate_financials(ev: Evaluation, model: CashFlowModel, tmp: str = ""):
    """1. Independent re-computation of the core metrics."""
    # Balance = initial + received - spent
    received = sum(i.received_amount for i in model.invoices
                   if i.status == PaymentStatus.RECEIVED)
    spent = sum(e.amount for e in model.expenses)
    expected_balance = 100000 + received - spent
    ev.near("Balance = initial + received - spent",
            model.get_current_balance(), expected_balance)

    # Sales tax liability = (received + outstanding) * rate
    outstanding = sum(i.amount for i in model.invoices
                      if i.status in (PaymentStatus.PENDING, PaymentStatus.LATE))
    expected_liability = (received + outstanding) * model.sales_tax_rate
    ev.near("Sales tax liability", model.get_sales_tax_liability(),
            expected_liability)

    # Available cash = balance - liability
    ev.near("Available cash = balance - liability",
            model.get_available_cash(),
            model.get_current_balance() - expected_liability)

    # DSO = (weighted AR / total sales) * 30, recomputed independently
    weighted_ar = sum(i.amount * i.collection_probability for i in model.invoices
                      if i.status in (PaymentStatus.PENDING, PaymentStatus.LATE))
    total_sales = sum(i.amount for i in model.invoices)
    expected_dso = round((weighted_ar / total_sales) * 30, 1)
    ev.near("DSO matches independent formula", model.calculate_dso(),
            expected_dso, tol=0.1)

    # Burn rate = fixed + recurring variable - avg monthly income
    recurring_var = sum(e.amount for e in model.expenses
                        if e.expense_type == ExpenseType.VARIABLE and e.recurring)
    ev.near("Burn rate = fixed + recurring - income",
            model.calculate_burn_rate(),
            38000 + recurring_var - received)  # fixed = 3000 + 35000

    # Runway = available / burn (burn > 0 here)
    burn = model.calculate_burn_rate()
    ev.near("Runway = available / burn", model.calculate_runway(),
            model.get_available_cash() / burn, tol=0.05)

    # Tax-reserve honesty: reserved runway < raw-balance runway
    ev.check("Tax reserve shortens runway (honest)",
             model.calculate_runway() < model.get_current_balance() / burn,
             f"runway {model.calculate_runway():.2f} vs raw "
             f"{model.get_current_balance() / burn:.2f}")


def evaluate_forecast(ev: Evaluation, model: CashFlowModel, tmp: str = ""):
    """2. Forecast structural integrity and consistency."""
    forecast = model.forecast_cash_flow(months=12)

    ev.check("Forecast has 12 rows", len(forecast) == 12)
    required = ['month', 'projected_income', 'fixed_expenses', 'variable_expenses',
                'tax_expenses', 'sales_tax_expenses', 'total_expenses',
                'net_cash_flow', 'cumulative_balance']
    ev.check("Forecast has all columns", all(c in forecast.columns for c in required))

    # Month 0 anchor: cumulative = current balance + net
    ev.near("Month 0 = balance + net",
            forecast.iloc[0]['cumulative_balance'],
            model.get_current_balance() + forecast.iloc[0]['net_cash_flow'])

    # Continuity: cum[i] == cum[i-1] + net[i]
    ok = all(
        abs(forecast.iloc[i]['cumulative_balance']
            - (forecast.iloc[i - 1]['cumulative_balance']
               + forecast.iloc[i]['net_cash_flow'])) < 0.01
        for i in range(1, len(forecast))
    )
    ev.check("Cumulative balance is continuous (no jumps)", ok)

    # Total income over the window == invoices expected in-window + milestones
    # P1: 40000*0.95, P2: 30000*0.95, milestone: 50000 (L1 expected date is past -> out)
    expected_income = 40000 * 0.95 + 30000 * 0.95 + 50000
    ev.near("Total 12m income = expected collections + milestones",
            float(forecast['projected_income'].sum()), expected_income, tol=0.5)

    # Final balance = balance + sum(net cash flows)
    ev.near("Final balance = balance + sum(net)",
            forecast.iloc[-1]['cumulative_balance'],
            model.get_current_balance() + float(forecast['net_cash_flow'].sum()),
            tol=0.5)

    # Sales tax settles at quarter-end months (2,5,8,11) whenever income was earned
    tax_months = [i for i, r in forecast.iterrows() if r['sales_tax_expenses'] > 0]
    ev.check("Sales tax only settles on quarter-end months",
             set(tax_months) <= {2, 5, 8, 11}, f"got {tax_months}")
    ev.check("Sales tax settles on the first earning quarter", 2 in tax_months,
             f"got {tax_months}")

    # And a month that had zero income but is NOT a quarter-end never settles
    mid_months = [i for i, r in forecast.iterrows()
                  if i not in (2, 5, 8, 11)]
    ev.check("No sales tax outside quarter-ends",
             all(r['sales_tax_expenses'] == 0
                 for i, r in forecast.iterrows() if i not in (2, 5, 8, 11)),
             f"mid months {[i for i in mid_months if forecast.loc[i, 'sales_tax_expenses'] > 0]}")


def evaluate_scenarios(ev: Evaluation, model: CashFlowModel, tmp: str = ""):
    """3. Scenarios, stress test and Monte Carlo behavior."""
    scenarios = {
        'Low': {'income_multiplier': 0.8},
        'Base': {},
        'High': {'income_multiplier': 1.2},
    }
    results = model.scenario_analysis(scenarios)
    ev.check("Scenario result per scenario", len(results) == 3)
    ev.check("Scenario columns present",
             all(c in results.columns for c in
                 ['scenario', 'final_balance', 'minimum_balance', 'survives']))

    by_name = {r['scenario']: r for _, r in results.iterrows()}
    ev.check("Higher income -> higher final balance (monotonic)",
             by_name['Low']['final_balance'] < by_name['Base']['final_balance']
             < by_name['High']['final_balance'],
             f"Low {by_name['Low']['final_balance']:.0f}, "
             f"Base {by_name['Base']['final_balance']:.0f}, "
             f"High {by_name['High']['final_balance']:.0f}")

    # The model must flag insolvency honestly (this firm runs out of cash)
    ev.check("Base case flagged as NOT surviving",
             by_name['Base']['survives'] is False,
             "model says the firm survives - check data")

    # Stress test
    stress = model.stress_test([0.9, 0.7, 0.5])
    ev.check("Stress test concatenates levels", len(stress) == 3)
    ev.check("Stress test has stress_level column", 'stress_level' in stress.columns)
    ev.check("More stress -> worse final balance",
             stress.iloc[-1]['final_balance'] < stress.iloc[0]['final_balance'])

    # Monte Carlo
    mc1 = model.monte_carlo(n_simulations=250, months=12, seed=11,
                            income_volatility=0.1, bad_debt_probability=0.05)
    mc2 = model.monte_carlo(n_simulations=250, months=12, seed=11,
                            income_volatility=0.1, bad_debt_probability=0.05)
    ev.check("Monte Carlo deterministic with seed",
             mc1['survival_probability'] == mc2['survival_probability'])
    pct = mc1['percentiles']
    ev.check("Monte Carlo P10 <= P50 <= P90",
             ((pct['p10'] <= pct['p50']) & (pct['p50'] <= pct['p90'])).all())
    ev.check("Survival probability in [0,1]", 0 <= mc1['survival_probability'] <= 1)

    # Bad debt must not improve survival
    b_clean = model.monte_carlo(n_simulations=250, months=12, seed=5,
                                income_volatility=0, expense_volatility=0,
                                bad_debt_probability=0)
    b_default = model.monte_carlo(n_simulations=250, months=12, seed=5,
                                  income_volatility=0, expense_volatility=0,
                                  bad_debt_probability=1.0)
    ev.check("Bad debt does not improve survival",
             b_default['survival_probability'] <= b_clean['survival_probability'],
             f"{b_default['survival_probability']} vs {b_clean['survival_probability']}")


def evaluate_roundtrips(ev: Evaluation, model: CashFlowModel, tmp: str):
    """4. Model -> save -> load fidelity (JSON, CSV, Excel)."""
    # JSON
    json_path = os.path.join(tmp, 'rt.json')
    ScenarioLoader.save_as_json(model, json_path)
    jm = ScenarioLoader.load_from_json(json_path)
    ev.check("JSON round-trip: invoice count",
             len(jm.invoices) == len(model.invoices))
    ev.check("JSON round-trip: balance preserved",
             abs(jm.get_current_balance() - model.get_current_balance()) < 0.01)
    ev.check("JSON round-trip: sales tax rate preserved",
             abs(jm.sales_tax_rate - model.sales_tax_rate) < 1e-9)

    # CSV
    csv_dir = os.path.join(tmp, 'csv')
    ScenarioLoader.save_as_csv(model, csv_dir)
    cm = ScenarioLoader.load_from_csv(
        config_csv=os.path.join(csv_dir, 'config.csv'),
        invoices_csv=os.path.join(csv_dir, 'invoices.csv'),
        expenses_csv=os.path.join(csv_dir, 'expenses.csv'),
        projects_csv=os.path.join(csv_dir, 'projects.csv'),
    )
    ev.check("CSV round-trip: invoice count",
             len(cm.invoices) == len(model.invoices))
    ev.check("CSV round-trip: project count",
             len(cm.projects) == len(model.projects))
    ev.check("CSV round-trip: balance preserved",
             abs(cm.get_current_balance() - model.get_current_balance()) < 0.01)
    ev.check("CSV round-trip: sales tax rate preserved",
             abs(cm.sales_tax_rate - model.sales_tax_rate) < 1e-9)

    # Excel (build the load-format workbook from the model)
    xlsx_path = os.path.join(tmp, 'rt.xlsx')
    now = datetime.now()
    config_df = pd.DataFrame([
        ['initial_balance', model.initial_balance],
        ['dpo_days', model.dpo_days],
        ['dio_days', model.dio_days],
        ['tax_rate', model.tax_rate],
        ['sales_tax_rate', model.sales_tax_rate],
    ], columns=['key', 'value'])
    invoices_df = pd.DataFrame([{
        'invoice_id': i.invoice_id, 'client': i.client, 'amount': i.amount,
        'issue_date': i.issue_date, 'due_date': i.due_date,
        'payment_terms_days': i.payment_terms_days, 'status': i.status.value,
        'received_date': i.received_date, 'received_amount': i.received_amount,
    } for i in model.invoices])
    expenses_df = pd.DataFrame([{
        'expense_id': e.expense_id, 'description': e.description,
        'amount': e.amount, 'date': e.date, 'expense_type': e.expense_type.value,
        'category': e.category, 'recurring': e.recurring,
    } for e in model.expenses])
    projects_df = pd.DataFrame([{
        'project_id': p.project_id, 'client': p.client, 'total_value': p.total_value,
        'start_date': p.start_date, 'estimated_end_date': p.estimated_end_date,
        'payments_received': p.payments_received,
        'work_completion_pct': p.work_completion_pct,
        'milestones_json': '[{"name":"Delivery","amount":50000,"date":"2026-03-01","paid":false}]',
    } for p in model.projects])
    with pd.ExcelWriter(xlsx_path, engine='openpyxl') as writer:
        config_df.to_excel(writer, sheet_name='Config', index=False)
        invoices_df.to_excel(writer, sheet_name='Invoices', index=False)
        expenses_df.to_excel(writer, sheet_name='Expenses', index=False)
        projects_df.to_excel(writer, sheet_name='Projects', index=False)
    xm = ScenarioLoader.load_from_excel(xlsx_path)
    ev.check("Excel round-trip: invoice count",
             len(xm.invoices) == len(model.invoices))
    ev.check("Excel round-trip: balance preserved",
             abs(xm.get_current_balance() - model.get_current_balance()) < 0.01)
    ev.check("Excel round-trip: sales tax rate preserved",
             abs(xm.sales_tax_rate - model.sales_tax_rate) < 1e-9)


def evaluate_artifacts(ev: Evaluation, model: CashFlowModel, tmp: str):
    """5. Every output the tool can produce must render without error."""
    # Excel report
    report = os.path.join(tmp, 'report.xlsx')
    model.export_to_excel(report)
    ev.check("Excel export creates file", os.path.exists(report))
    if os.path.exists(report):
        xls = pd.ExcelFile(report)
        for sheet in ['Dashboard', 'Forecast', 'Client Analysis', 'AR Aging', 'Invoices']:
            ev.check(f"Excel export has sheet {sheet}", sheet in xls.sheet_names)

    # Matplotlib dashboards (regression: plot_cash_conversion_cycle used to crash)
    dash = CashFlowDashboard(model)
    p1 = os.path.join(tmp, 'dash.png')
    dash.create_full_dashboard(save_path=p1)
    ev.check("Full dashboard PNG renders", os.path.exists(p1) and os.path.getsize(p1) > 0)

    p2 = os.path.join(tmp, 'mc.png')
    dash.plot_monte_carlo(save_path=p2)
    ev.check("Monte Carlo band PNG renders",
             os.path.exists(p2) and os.path.getsize(p2) > 0)

    p3 = os.path.join(tmp, 'ccc.png')
    dash.plot_cash_conversion_cycle(save_path=p3)
    ev.check("Cash conversion cycle PNG renders (regression)",
             os.path.exists(p3) and os.path.getsize(p3) > 0)

    # Interactive HTML dashboard
    html = generate_html_dashboard()
    ev.check("HTML dashboard generated", '<html' in html.lower()
             and 'Chart' in html)


def evaluate_connectors(ev: Evaluation, model: CashFlowModel, tmp: str):
    """6. API connector integration on the full pipeline."""
    now = datetime.now()
    ts = int((now - timedelta(days=15)).timestamp())
    payload = {
        'invoices': [
            {'id': 'in_1', 'customer_name': 'Acme', 'status': 'paid',
             'created': ts, 'total': 250000},
            {'id': 'in_2', 'customer_email': 'b@x.com', 'status': 'open',
             'created': ts, 'amount_due': 100000},
        ],
        'payments': [{'invoice': 'in_1', 'created': ts, 'amount_captured': 250000}],
        'expenses': [{'id': 'py_1', 'description': 'Hosting', 'amount': 5000,
                      'created': ts, 'category': 'Infra',
                      'expense_type': 'variable', 'recurring': True}],
    }
    cm = ScenarioLoader.load_from_connector(
        StripeConnector(), data=payload,
        config={'initial_balance': 10000, 'sales_tax_rate': 0.21}
    )
    ev.check("Connector builds 2 invoices", len(cm.invoices) == 2)
    ev.check("Connector builds 1 expense", len(cm.expenses) == 1)

    # The imported model must run the full pipeline
    dashboard = cm.generate_dashboard_data()
    ev.check("Connector dashboard computes",
             'available_cash' in dashboard and dashboard['current_balance'] > 0)
    forecast = cm.forecast_cash_flow(months=12)
    ev.check("Connector forecast runs", len(forecast) == 12)
    mc = cm.monte_carlo(n_simulations=50, months=6, seed=3)
    ev.check("Connector Monte Carlo runs", 0 <= mc['survival_probability'] <= 1)
    report = os.path.join(tmp, 'connector.xlsx')
    cm.export_to_excel(report)
    ev.check("Connector Excel export runs", os.path.exists(report))


def evaluate_flag(ev: Evaluation, model: CashFlowModel, tmp: str = ""):
    """7. The model must say NO when it should (no false comfort)."""
    forecast = model.forecast_cash_flow(months=12)
    min_balance = float(forecast['cumulative_balance'].min())
    ev.check("Model detects cash insolvency (min balance < 0)",
             min_balance < 0, f"min balance {min_balance:.0f}")
    runway = model.calculate_runway()
    ev.check("Finite (not infinite) runway for a loss-making firm",
             runway != float('inf'), f"runway {runway}")


def main():
    print("=" * 70)
    print("CASH FLOW MODEL - END-TO-END EVALUATION")
    print("=" * 70)

    sections = [
        ("1. Financial invariants", evaluate_financials),
        ("2. Forecast integrity", evaluate_forecast),
        ("3. Scenario / stress / Monte Carlo", evaluate_scenarios),
        ("4. Loader round-trips (JSON/CSV/Excel)", evaluate_roundtrips),
        ("5. Output artifacts", evaluate_artifacts),
        ("6. API connectors", evaluate_connectors),
        ("7. Honest insolvency flag", evaluate_flag),
    ]

    all_results = []
    tmp = tempfile.mkdtemp(prefix='cfm_eval_')
    try:
        model = build_full_model()
        for title, fn in sections:
            print(f"\n[{title}]")
            ev = Evaluation(title)
            fn(ev, model, tmp)
            all_results.append(ev)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    total_pass = sum(e.passed for e in all_results)
    total_fail = sum(e.failed for e in all_results)
    total = total_pass + total_fail
    score = (total_pass / total * 100) if total else 0

    print(f"\n{'=' * 70}")
    print(f"EVALUATION RESULTS: {total_pass}/{total} checks passed ({score:.0f}%)")
    if total_fail:
        print("\nFAILURES:")
        for e in all_results:
            for err in e.errors:
                print(f"  - {err}")
        sys.exit(1)
    print("ALL CHECKS PASSED")
    print(f"{'=' * 70}")
    return 0


if __name__ == '__main__':
    main()
