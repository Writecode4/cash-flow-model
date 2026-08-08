"""
Test Suite - Cash Flow Model Formula Validation
================================================
Auditoria senior: Todos los calculos verificados contra definiciones estandar.

Run: python test_suite.py
"""

import sys
from datetime import datetime, timedelta
from cash_flow_model import (
    CashFlowModel, Invoice, Expense, Project,
    PaymentStatus, ExpenseType
)
from connectors.stripe import StripeConnector, ConnectorError
from connectors.quickbooks import QuickBooksConnector
from scenario_loader import ScenarioLoader


class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def check(self, name, condition, detail=""):
        if condition:
            self.passed += 1
            print(f"  [PASS] {name}")
        else:
            self.failed += 1
            self.errors.append(f"{name}: {detail}")
            print(f"  [FAIL] {name} - {detail}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"RESULTS: {self.passed}/{total} passed, {self.failed} failed")
        if self.errors:
            print(f"\nFAILURES:")
            for e in self.errors:
                print(f"  - {e}")
        print(f"{'='*60}")
        return self.failed == 0


TODAY = datetime.now()

def days_ago(n):
    return TODAY - timedelta(days=n)

def days_from_now(n):
    return TODAY + timedelta(days=n)


def test_dso():
    """DSO = (AR / Credit Sales) x 30"""
    print("\n[DSO - Days Sales Outstanding]")
    results = TestResults()
    
    # Case 1: No invoices -> DSO = 0
    m = CashFlowModel(initial_balance=100000)
    results.check("No invoices => DSO=0", m.calculate_dso() == 0)
    
    # Case 2: All received -> DSO = 0 (no AR)
    m = CashFlowModel(initial_balance=100000)
    m.add_invoice(Invoice("I1", "C1", 10000, days_ago(40), days_ago(10), 30,
                          PaymentStatus.RECEIVED, days_ago(8), 10000))
    results.check("All received => DSO=0", m.calculate_dso() == 0)
    
    # Case 3: Single pending invoice (10 days old -> 95% prob)
    m = CashFlowModel(initial_balance=100000)
    m.add_invoice(Invoice("I1", "C1", 30000, days_ago(10), days_from_now(20), 30,
                          PaymentStatus.PENDING))
    # AR = 30000 * 0.95 = 28500
    # DSO = (28500 / 30000) * 30 = 28.5
    dso = m.calculate_dso()
    results.check("Single pending 30k, 10d old => DSO=28.5", abs(dso - 28.5) < 0.1, f"got {dso}")
    
    # Case 4: Multiple invoices, mixed status
    m = CashFlowModel(initial_balance=100000)
    m.add_invoice(Invoice("I1", "C1", 20000, days_ago(40), days_ago(10), 30,
                          PaymentStatus.RECEIVED, days_ago(8), 20000))
    m.add_invoice(Invoice("I2", "C2", 40000, days_ago(10), days_from_now(20), 30,
                          PaymentStatus.PENDING))
    # AR = 40000 * 0.95 = 38000 (only pending counts)
    # Total sales = 60000
    # DSO = (38000/60000)*30 = 19.0
    dso = m.calculate_dso()
    results.check("Mixed status => DSO=19.0", abs(dso - 19.0) < 0.1, f"got {dso}")
    
    # Case 5: Late invoice (75 days old -> 65% prob)
    m = CashFlowModel(initial_balance=100000)
    m.add_invoice(Invoice("I1", "C1", 10000, days_ago(75), days_ago(45), 30,
                          PaymentStatus.LATE, None, 0))
    # AR = 10000 * 0.65 = 6500
    # DSO = (6500/10000)*30 = 19.5
    dso = m.calculate_dso()
    results.check("Late invoice 75d => DSO~19.5", abs(dso - 19.5) < 1.0, f"got {dso}")
    
    # Case 6: DSO raw (no collection weighting)
    # DSO = (AR / Total Sales) * 30. If AR = Sales, DSO = 30.
    m = CashFlowModel(initial_balance=100000)
    m.add_invoice(Invoice("I1", "C1", 50000, days_ago(10), days_from_now(20), 30,
                          PaymentStatus.PENDING))
    dso_raw = m.calculate_dso_raw()
    results.check("DSO raw = 30.0 (AR=Sales => DSO=period)", abs(dso_raw - 30.0) < 0.1, f"got {dso_raw}")
    
    return results


def test_dpo():
    """DPO configurable, default 30"""
    print("\n[DPO - Days Payable Outstanding]")
    results = TestResults()
    
    m = CashFlowModel()
    results.check("Default DPO=30", m.dpo_days == 30)
    
    m.set_dpo_days(45)
    results.check("Set DPO=45", m.dpo_days == 45)
    
    m.set_dpo_days(0)
    results.check("Set DPO=0", m.dpo_days == 0)
    
    try:
        m.set_dpo_days(-5)
        results.check("Negative DPO rejected", False, "Should have raised ValueError")
    except ValueError:
        results.check("Negative DPO rejected", True)
    
    return results


def test_dio():
    """DIO configurable, default 0"""
    print("\n[DIO - Days Inventory Outstanding]")
    results = TestResults()
    
    m = CashFlowModel()
    results.check("Default DIO=0", m.dio_days == 0)
    
    m.set_dio_days(15)
    results.check("Set DIO=15", m.dio_days == 15)
    
    return results


def test_ccc():
    """CCC = DSO + DIO - DPO"""
    print("\n[CCC - Cash Conversion Cycle]")
    results = TestResults()
    
    m = CashFlowModel(initial_balance=100000)
    m.set_dpo_days(30)
    m.set_dio_days(0)
    m.add_invoice(Invoice("I1", "C1", 10000, days_ago(10), days_from_now(20), 30,
                          PaymentStatus.PENDING))
    dso = m.calculate_dso()
    ccc = m.calculate_cash_conversion_cycle()
    expected = dso + 0 - 30
    results.check(f"CCC = DSO({dso}) + DIO(0) - DPO(30) = {expected}", abs(ccc - expected) < 0.1, f"got {ccc}")
    
    m.set_dio_days(15)
    ccc = m.calculate_cash_conversion_cycle()
    expected = dso + 15 - 30
    results.check(f"CCC with DIO=15 => {expected}", abs(ccc - expected) < 0.1, f"got {ccc}")
    
    return results


def test_burn_rate():
    """Burn Rate = Monthly Expenses - Monthly Income"""
    print("\n[Burn Rate]")
    results = TestResults()
    
    m = CashFlowModel(initial_balance=100000)
    m.set_monthly_fixed_costs({'rent': 5000, 'salaries': 20000})
    burn = m.calculate_burn_rate()
    results.check("Fixed 25k, no income => burn=25000", abs(burn - 25000) < 0.1, f"got {burn}")
    
    m = CashFlowModel(initial_balance=100000)
    m.set_monthly_fixed_costs({'rent': 5000})
    m.add_expense(Expense("E1", "Cloud", 1000, TODAY, ExpenseType.VARIABLE, "Infra", True))
    m.add_expense(Expense("E2", "Processing", 500, TODAY, ExpenseType.VARIABLE, "Infra", True))
    burn = m.calculate_burn_rate()
    results.check("Fixed 5k + Variable 1.5k => burn=6500", abs(burn - 6500) < 0.1, f"got {burn}")
    
    m = CashFlowModel(initial_balance=100000)
    m.set_monthly_fixed_costs({'rent': 5000})
    m.add_invoice(Invoice("I1", "C1", 30000, days_ago(40), days_ago(10), 30,
                          PaymentStatus.RECEIVED, days_ago(8), 30000))
    m.add_invoice(Invoice("I2", "C2", 30000, days_ago(70), days_ago(40), 30,
                          PaymentStatus.RECEIVED, days_ago(38), 30000))
    burn = m.calculate_burn_rate()
    results.check("Income > expenses => negative burn", burn < 0, f"got {burn}")
    
    m = CashFlowModel(initial_balance=100000)
    m.set_monthly_fixed_costs({'rent': 5000})
    m.add_expense(Expense("E1", "Legal", 10000, TODAY, ExpenseType.ONE_TIME, "Legal", False))
    burn = m.calculate_burn_rate()
    results.check("One-time excluded from burn", abs(burn - 5000) < 0.1, f"got {burn}")
    
    return results


def test_runway():
    """Runway = Balance / Burn Rate"""
    print("\n[Runway]")
    results = TestResults()
    
    m = CashFlowModel(initial_balance=100000)
    m.set_monthly_fixed_costs({'rent': 5000})
    m.add_invoice(Invoice("I1", "C1", 50000, days_ago(10), days_from_now(20), 30,
                          PaymentStatus.RECEIVED, days_ago(8), 50000))
    runway = m.calculate_runway()
    results.check("Cash positive => infinite runway", runway == float('inf'))
    
    m = CashFlowModel(initial_balance=100000)
    m.set_monthly_fixed_costs({'rent': 10000})
    runway = m.calculate_runway()
    results.check("100k balance / 10k burn => 10 months", abs(runway - 10.0) < 0.1, f"got {runway}")
    
    m = CashFlowModel(initial_balance=0)
    m.set_monthly_fixed_costs({'rent': 10000})
    runway = m.calculate_runway()
    results.check("Zero balance => runway=0", runway == 0)
    
    return results


def test_collection_probability():
    """Collection probability by aging bucket"""
    print("\n[Collection Probability]")
    results = TestResults()
    
    inv = Invoice("I1", "C1", 10000, days_ago(10), days_from_now(20), 30,
                  PaymentStatus.RECEIVED, TODAY, 10000)
    results.check("Received => 100%", inv.collection_probability == 1.0)
    
    inv = Invoice("I1", "C1", 10000, days_ago(120), days_ago(90), 30,
                  PaymentStatus.DEFAULTED)
    results.check("Defaulted => 0%", inv.collection_probability == 0.0)
    
    inv = Invoice("I1", "C1", 10000, days_ago(10), days_from_now(20), 30,
                  PaymentStatus.PENDING)
    results.check("0-30 days => 95%", inv.collection_probability == 0.95)
    
    inv = Invoice("I1", "C1", 10000, days_ago(45), days_ago(15), 30,
                  PaymentStatus.PENDING)
    results.check("31-60 days => 85%", inv.collection_probability == 0.85)
    
    inv = Invoice("I1", "C1", 10000, days_ago(75), days_ago(45), 30,
                  PaymentStatus.PENDING)
    results.check("61-90 days => 65%", inv.collection_probability == 0.65)
    
    inv = Invoice("I1", "C1", 10000, days_ago(120), days_ago(90), 30,
                  PaymentStatus.PENDING)
    results.check("90+ days => 40%", inv.collection_probability == 0.40)
    
    inv = Invoice("I1", "C1", 10000, days_ago(10), days_from_now(20), 30,
                  PaymentStatus.PENDING)
    inv._collection_rate_override = 0.75
    results.check("Override field => 75%", inv.collection_probability == 0.75)
    
    return results


def test_tax_estimation():
    """Quarterly tax payments in the 3rd month of each forecast quarter"""
    print("\n[Tax Estimation]")
    results = TestResults()
    
    m = CashFlowModel(initial_balance=1000000)
    m.set_monthly_fixed_costs({'cost': 10000})
    m.set_tax_rate(0.25)
    
    # Income in the first forecast month
    m.add_invoice(Invoice("I1", "C1", 50000, days_ago(5), days_from_now(5), 5,
                          PaymentStatus.PENDING))
    
    forecast = m.forecast_cash_flow(months=12)
    
    # Check which months have tax > 0
    tax_months = [i for i, row in forecast.iterrows() if row['tax_expenses'] > 0]
    
    # Tax should appear in quarter-end months (forecast-relative: indices 2, 5, 8, 11)
    results.check("Tax calculated in some months", len(tax_months) > 0, f"got months {tax_months}")
    
    # Verify quarterly pattern: tax should appear every 3 months
    if len(tax_months) >= 2:
        gaps = [tax_months[i+1] - tax_months[i] for i in range(len(tax_months)-1)]
        results.check("Tax is quarterly (3-month gaps)", all(g == 3 for g in gaps), f"gaps={gaps}")
    
    # Verify tax equals tax_rate * quarterly profit (accumulated, not single-month)
    positive_quarters = [i for i, row in forecast.iterrows() if row['tax_expenses'] > 0]
    if positive_quarters:
        idx = positive_quarters[0]
        q_start = idx - 2
        q_profit = sum(
            (forecast.iloc[j]['projected_income']
             - forecast.iloc[j]['fixed_expenses']
             - forecast.iloc[j]['variable_expenses']) for j in range(q_start, idx + 1)
        )
        expected = max(q_profit, 0) * 0.25
        results.check("Tax = rate x quarterly accumulated profit",
                      abs(forecast.iloc[idx]['tax_expenses'] - expected) < 0.01,
                      f"got {forecast.iloc[idx]['tax_expenses']}, expected {expected}")
    
    return results


def test_milestone_deduplication():
    """Milestone-invoice deduplication"""
    print("\n[Milestone Deduplication]")
    results = TestResults()
    
    # Case 1: Milestone with explicit invoice_id -> excluded
    m = CashFlowModel(initial_balance=100000)
    m.add_project(Project("P1", "Client A", 50000, days_ago(20), days_from_now(10),
                          [{'name': 'MS1', 'amount': 25000, 'date': days_from_now(5),
                            'paid': False, 'invoice_id': 'INV-001'}], 0, 50))
    m.add_invoice(Invoice("INV-001", "Client A", 25000, days_ago(5),
                          days_from_now(25), 30, PaymentStatus.PENDING))
    
    forecast = m.forecast_cash_flow(months=1)
    income = forecast.iloc[0]['projected_income']
    # Invoice contributes: 25000 * 0.95 = 23750
    # Milestone excluded
    results.check("Linked milestone excluded", income < 25000, f"income={income}")
    
    # Case 2: Milestone without invoice_id, amount matches -> excluded (fallback)
    m = CashFlowModel(initial_balance=100000)
    m.add_project(Project("P1", "Client A", 50000, days_ago(20), days_from_now(10),
                          [{'name': 'MS1', 'amount': 25000, 'date': days_from_now(5),
                            'paid': False}], 0, 50))
    m.add_invoice(Invoice("INV-001", "Client A", 25000, days_ago(5),
                          days_from_now(25), 30, PaymentStatus.PENDING))
    
    forecast = m.forecast_cash_flow(months=1)
    income = forecast.iloc[0]['projected_income']
    results.check("Amount-matched milestone excluded (fallback)", income < 25000, f"income={income}")
    
    # Case 3: Milestone with different amount -> both counted
    # Invoice expected payment and milestone both in current month
    m = CashFlowModel(initial_balance=100000)
    m.add_project(Project("P1", "Client A", 50000, days_ago(20), days_from_now(10),
                          [{'name': 'MS1', 'amount': 30000, 'date': days_from_now(5),
                            'paid': False}], 0, 50))
    # Invoice with 5-day terms -> expected payment in ~5 days (same month as milestone)
    m.add_invoice(Invoice("INV-001", "Client A", 25000, days_ago(2),
                          days_from_now(5), 5, PaymentStatus.PENDING))
    
    forecast = m.forecast_cash_flow(months=1)
    income = forecast.iloc[0]['projected_income']
    # Invoice: 25000 * 0.95 = 23750
    # Milestone: 30000 (included, different amount)
    # Total: 53750
    results.check("Unmatched milestone + invoice both counted", income >= 50000, f"income={income}")
    
    return results


def test_edge_cases():
    """Edge cases and boundary conditions"""
    print("\n[Edge Cases]")
    results = TestResults()
    
    m = CashFlowModel(initial_balance=0)
    results.check("Empty model balance=0", m.get_current_balance() == 0)
    results.check("Empty model DSO=0", m.calculate_dso() == 0)
    results.check("Empty model burn=0", m.calculate_burn_rate() == 0)
    
    try:
        CashFlowModel(initial_balance=-1000)
        results.check("Negative balance rejected", False)
    except ValueError:
        results.check("Negative balance rejected", True)
    
    try:
        Invoice("I1", "C1", 0, TODAY, TODAY, 30)
        results.check("Zero amount invoice rejected", False)
    except ValueError:
        results.check("Zero amount invoice rejected", True)
    
    try:
        Invoice("I1", "C1", 1000, TODAY, TODAY, 30,
                PaymentStatus.RECEIVED, TODAY, 2000)
        results.check("Received > amount rejected", False)
    except ValueError:
        results.check("Received > amount rejected", True)
    
    try:
        m = CashFlowModel()
        m.set_tax_rate(1.5)
        results.check("Tax rate >1 rejected", False)
    except ValueError:
        results.check("Tax rate >1 rejected", True)
    
    return results


def test_sales_tax():
    """Sales tax (VAT/IVA) liability and available cash"""
    print("\n[Sales Tax (IVA/VAT)]")
    results = TestResults()
    
    m = CashFlowModel(initial_balance=50000)
    m.add_invoice(Invoice("I1", "C1", 10000, days_ago(10), days_from_now(20), 30,
                          PaymentStatus.RECEIVED, days_ago(8), 10000))
    
    # Default sales tax = 0 -> no liability
    results.check("No sales tax => liability 0", m.get_sales_tax_liability() == 0)
    results.check("No sales tax => available = balance",
                  abs(m.get_available_cash() - m.get_current_balance()) < 0.001)
    
    m.set_sales_tax_rate(0.21)  # 21% IVA
    # Received 10000 * 0.21 = 2100 owed
    results.check("Liability on received", abs(m.get_sales_tax_liability() - 2100) < 0.01,
                  f"got {m.get_sales_tax_liability()}")
    results.check("Available = balance - liability",
                  abs(m.get_available_cash() - (m.get_current_balance() - 2100)) < 0.01)
    
    # Pending invoice also accrues liability (conservative)
    m.add_invoice(Invoice("I2", "C2", 20000, days_ago(5), days_from_now(25), 30,
                          PaymentStatus.PENDING))
    results.check("Liability includes outstanding",
                  abs(m.get_sales_tax_liability() - (10000 + 20000) * 0.21) < 0.01,
                  f"got {m.get_sales_tax_liability()}")
    
    # Validation
    try:
        m.set_sales_tax_rate(1.5)
        results.check("Sales tax rate >1 rejected", False)
    except ValueError:
        results.check("Sales tax rate >1 rejected", True)
    
    return results


def test_monte_carlo():
    """Monte Carlo simulation determinism and output structure"""
    print("\n[Monte Carlo]")
    results = TestResults()
    
    m = CashFlowModel(initial_balance=100000)
    m.set_monthly_fixed_costs({'cost': 20000})
    m.add_invoice(Invoice("I1", "C1", 50000, days_ago(5), days_from_now(25), 30,
                          PaymentStatus.PENDING))
    
    # Deterministic with seed
    a = m.monte_carlo(n_simulations=200, months=12, seed=7,
                      income_volatility=0.1, bad_debt_probability=0.05)
    b = m.monte_carlo(n_simulations=200, months=12, seed=7,
                      income_volatility=0.1, bad_debt_probability=0.05)
    results.check("Same seed => same result",
                  a['survival_probability'] == b['survival_probability']
                  and (a['percentiles'].values == b['percentiles'].values).all())
    
    # Structure
    results.check("Percentiles has 12 rows", len(a['percentiles']) == 12)
    results.check("Has p10/p50/p90 columns",
                  all(c in a['percentiles'].columns for c in ['p10', 'p50', 'p90']))
    results.check("Survival prob in [0,1]", 0 <= a['survival_probability'] <= 1)
    results.check("n_simulations reported", a['n_simulations'] == 200)
    results.check("Final balance has p10/p50/p90",
                  all(k in a['final_balance'] for k in ['p10', 'p50', 'p90']))
    
    # P10 <= P50 <= P90 per month
    pct = a['percentiles']
    monotone = ((pct['p10'] <= pct['p50']) & (pct['p50'] <= pct['p90'])).all()
    results.check("P10 <= P50 <= P90", monotone)
    
    # Validation
    try:
        m.monte_carlo(n_simulations=0)
        results.check("n_simulations=0 rejected", False)
    except ValueError:
        results.check("n_simulations=0 rejected", True)
    
    return results


def test_stripe_connector():
    """Stripe connector: parsing and model building"""
    print("\n[Stripe Connector]")
    results = TestResults()
    today = datetime.now()
    created_ts = int((today - timedelta(days=30)).timestamp())
    due_ts = int((today + timedelta(days=30)).timestamp())
    paid_ts = int((today - timedelta(days=10)).timestamp())

    # --- parse_invoice: paid invoice linked to a charge ---
    inv = StripeConnector.parse_invoice(
        {'id': 'in_1', 'customer_name': 'Acme', 'status': 'paid',
         'created': created_ts, 'due_date': due_ts, 'total': 2500000},  # 25000.00
        payments=[{'invoice': 'in_1', 'created': paid_ts, 'amount_captured': 2500000}]
    )
    results.check("Paid invoice mapped to RECEIVED", inv.status == PaymentStatus.RECEIVED)
    results.check("Minor->major conversion (cents / 100)", abs(inv.amount - 25000) < 0.01, f"got {inv.amount}")
    results.check("Received amount from charge", abs(inv.received_amount - 25000) < 0.01)
    results.check("Received date from charge", inv.received_date is not None)
    results.check("Payment terms derived", inv.payment_terms_days == 60)

    # --- open invoice -> PENDING ---
    inv = StripeConnector.parse_invoice(
        {'id': 'in_2', 'customer_email': 'b@x.com', 'status': 'open',
         'created': created_ts, 'amount_due': 100000}
    )
    results.check("Open invoice mapped to PENDING", inv.status == PaymentStatus.PENDING)
    results.check("Open invoice no received amount", inv.received_amount == 0)

    # --- past_due -> LATE ---
    inv = StripeConnector.parse_invoice(
        {'id': 'in_3', 'status': 'past_due', 'created': created_ts, 'total': 500000}
    )
    results.check("past_due mapped to LATE", inv.status == PaymentStatus.LATE)

    # --- uncollectible -> DEFAULTED ---
    inv = StripeConnector.parse_invoice(
        {'id': 'in_4', 'status': 'uncollectible', 'created': created_ts, 'total': 500000}
    )
    results.check("uncollectible mapped to DEFAULTED", inv.status == PaymentStatus.DEFAULTED)
    results.check("Defaulted collection prob 0", inv.collection_probability == 0.0)

    # --- draft/void skipped ---
    inv = StripeConnector.parse_invoice({'id': 'in_5', 'status': 'draft', 'total': 100})
    results.check("Draft invoice skipped", inv is None)

    # --- missing id -> ConnectorError ---
    try:
        StripeConnector.parse_invoice({'status': 'open', 'total': 100})
        results.check("Missing id raises", False)
    except ConnectorError:
        results.check("Missing id raises", True)

    # --- to_model builds a complete model ---
    payload = {
        'invoices': [
            {'id': 'in_1', 'customer_name': 'Acme', 'status': 'paid',
             'created': created_ts, 'due_date': due_ts, 'total': 2500000},
            {'id': 'in_2', 'customer_email': 'b@x.com', 'status': 'open',
             'created': created_ts, 'amount_due': 100000},
            {'id': 'in_3', 'status': 'draft', 'total': 999},
        ],
        'payments': [],
        'expenses': [
            {'id': 'py_1', 'description': 'Hosting', 'amount': 50000,
             'created': created_ts, 'category': 'Infra', 'expense_type': 'variable', 'recurring': True}
        ],
    }
    model = StripeConnector().to_model(
        payload,
        config={'initial_balance': 10000, 'sales_tax_rate': 0.21,
                'monthly_fixed_costs': {'rent': 2000}}
    )
    results.check("Model has 2 invoices (draft skipped)", len(model.invoices) == 2)
    results.check("Model has 1 expense", len(model.expenses) == 1)
    results.check("Sales tax rate applied", model.sales_tax_rate == 0.21)
    results.check("Fixed costs applied", model.monthly_fixed_costs.get('rent') == 2000)
    results.check("Balance reflects received",
                  abs(model.get_current_balance() - (10000 + 25000 - 500)) < 0.01,
                  f"got {model.get_current_balance()}")
    results.check("Forecast runs on connector model", len(model.forecast_cash_flow(months=6)) == 6)

    # --- fetch requires key/SDK ---
    try:
        StripeConnector().fetch()
        results.check("fetch without key raises", False)
    except ConnectorError:
        results.check("fetch without key raises", True)

    return results


def test_quickbooks_connector():
    """QuickBooks connector: parsing and model building"""
    print("\n[QuickBooks Connector]")
    results = TestResults()
    today = datetime.now()
    iso_today = today.strftime('%Y-%m-%d')
    iso_30 = (today - timedelta(days=30)).strftime('%Y-%m-%d')
    iso_60 = (today - timedelta(days=60)).strftime('%Y-%m-%d')
    iso_30ahead = (today + timedelta(days=30)).strftime('%Y-%m-%d')

    # --- paid invoice (Balance 0) linked to a payment ---
    inv = QuickBooksConnector.parse_invoice(
        {'Id': '123', 'CustomerRef': {'name': 'Acme'}, 'TotalAmt': 40000.0,
         'Balance': 0.0, 'TxnDate': iso_60, 'DueDate': iso_30},
        payments=[{'TxnDate': iso_30, 'TotalAmt': 40000.0,
                   'LinkedTxn': [{'TxnId': '123'}]}]
    )
    results.check("Zero balance => RECEIVED", inv.status == PaymentStatus.RECEIVED)
    results.check("Received amount from linked payment", abs(inv.received_amount - 40000) < 0.01)
    results.check("Client name from CustomerRef", inv.client == 'Acme')

    # --- overdue (Balance > 0, DueDate past) -> LATE ---
    inv = QuickBooksConnector.parse_invoice(
        {'Id': '124', 'CustomerRef': {'name': 'Beta'}, 'TotalAmt': 10000.0,
         'Balance': 10000.0, 'TxnDate': iso_60, 'DueDate': iso_30}
    )
    results.check("Overdue mapped to LATE", inv.status == PaymentStatus.LATE)

    # --- pending (due in future) -> PENDING ---
    inv = QuickBooksConnector.parse_invoice(
        {'Id': '125', 'CustomerRef': {'name': 'Gamma'}, 'TotalAmt': 5000.0,
         'Balance': 5000.0, 'TxnDate': iso_today, 'DueDate': iso_30ahead}
    )
    results.check("Future due => PENDING", inv.status == PaymentStatus.PENDING)

    # --- explicit status defaulted ---
    inv = QuickBooksConnector.parse_invoice(
        {'Id': '126', 'CustomerRef': {'name': 'Delta'}, 'TotalAmt': 3000.0,
         'Balance': 3000.0, 'TxnDate': iso_60, 'DueDate': iso_30, 'status': 'defaulted'}
    )
    results.check("Explicit defaulted status", inv.status == PaymentStatus.DEFAULTED)

    # --- explicit void -> skipped ---
    inv = QuickBooksConnector.parse_invoice(
        {'Id': '127', 'TotalAmt': 1000.0, 'Balance': 1000.0, 'status': 'void'}
    )
    results.check("Void invoice skipped", inv is None)

    # --- missing Id -> ConnectorError ---
    try:
        QuickBooksConnector.parse_invoice({'TotalAmt': 1000.0})
        results.check("Missing Id raises", False)
    except ConnectorError:
        results.check("Missing Id raises", True)

    # --- to_model builds a complete model ---
    payload = {
        'invoices': [
            {'Id': '123', 'CustomerRef': {'name': 'Acme'}, 'TotalAmt': 40000.0,
             'Balance': 0.0, 'TxnDate': iso_60, 'DueDate': iso_30},
            {'Id': '124', 'CustomerRef': {'name': 'Beta'}, 'TotalAmt': 10000.0,
             'Balance': 10000.0, 'TxnDate': iso_60, 'DueDate': iso_30},
        ],
        'payments': [
            {'TxnDate': iso_30, 'TotalAmt': 40000.0, 'LinkedTxn': [{'TxnId': '123'}]}
        ],
        'expenses': [
            {'Id': '9', 'VendorRef': {'name': 'AWS'}, 'TotalAmt': 800.0,
             'TxnDate': iso_30, 'expense_type': 'variable', 'recurring': True}
        ],
    }
    model = QuickBooksConnector().to_model(payload, config={'initial_balance': 5000})
    results.check("Model has 2 invoices", len(model.invoices) == 2)
    results.check("Model has 1 expense", len(model.expenses) == 1)
    received = sum(i.received_amount for i in model.invoices)
    results.check("Balance reflects payment",
                  abs(model.get_current_balance() - (5000 + received - 800)) < 0.01,
                  f"got {model.get_current_balance()}")

    # --- fetch requires token/realm ---
    try:
        QuickBooksConnector().fetch()
        results.check("fetch without token raises", False)
    except ConnectorError:
        results.check("fetch without token raises", True)

    return results


def test_load_from_connector():
    """ScenarioLoader.load_from_connector orchestration"""
    print("\n[Load From Connector]")
    results = TestResults()
    today = datetime.now()
    created_ts = int((today - timedelta(days=20)).timestamp())

    class FakeConnector:
        def __init__(self):
            self.fetch_called = False

        def fetch(self):
            self.fetch_called = True
            return {
                'invoices': [{'id': 'in_1', 'status': 'open',
                              'created': created_ts, 'total': 150000}],
                'payments': [],
                'expenses': [],
            }

        def to_model(self, data, config=None):
            return StripeConnector().to_model(data, config=config)

    # Data provided -> fetch not called
    c = FakeConnector()
    model = ScenarioLoader.load_from_connector(
        c,
        data={'invoices': [{'id': 'in_2', 'status': 'paid',
                            'created': created_ts, 'total': 100000}],
              'payments': [], 'expenses': []},
        config={'sales_tax_rate': 0.21}
    )
    results.check("Data path does not call fetch", c.fetch_called is False)
    results.check("Model built from provided data", len(model.invoices) == 1)
    results.check("Config applied", model.sales_tax_rate == 0.21)

    # No data -> fetch called
    c = FakeConnector()
    model = ScenarioLoader.load_from_connector(c)
    results.check("No data path calls fetch", c.fetch_called is True)
    results.check("Model built from fetched data", len(model.invoices) == 1)

    return results


def test_full_scenario():
    """End-to-end scenario validation"""
    print("\n[Full Scenario - E2E]")
    results = TestResults()
    
    m = CashFlowModel(initial_balance=50000)
    m.set_dpo_days(30)
    m.set_tax_rate(0.25)
    m.set_monthly_fixed_costs({'rent': 3000, 'salaries': 15000})
    
    m.add_expense(Expense("E1", "Cloud", 800, TODAY, ExpenseType.VARIABLE, "Infra", True))
    
    m.add_invoice(Invoice("I1", "Client A", 20000, days_ago(40), days_ago(10), 30,
                          PaymentStatus.RECEIVED, days_ago(8), 20000))
    
    m.add_invoice(Invoice("I2", "Client B", 30000, days_ago(5), days_from_now(25), 30,
                          PaymentStatus.PENDING))
    
    m.add_project(Project("P1", "Client C", 60000, days_ago(20), days_from_now(40),
                          [{'name': 'Delivery', 'amount': 60000,
                            'date': days_from_now(30), 'paid': False}],
                          0, 40))
    
    try:
        balance = m.get_current_balance()
        dso = m.calculate_dso()
        burn = m.calculate_burn_rate()
        runway = m.calculate_runway()
        ccc = m.calculate_cash_conversion_cycle()
        forecast = m.forecast_cash_flow(months=12)
        ar = m.get_accounts_receivable()
        dashboard = m.generate_dashboard_data()
        
        results.check("All metrics compute", True)
        # Balance = 50000 + 20000 - 800 = 69200 (only received - expenses)
        results.check("Balance correct", abs(balance - 69200) < 0.1, f"got {balance}")
        results.check("Forecast has 12 rows", len(forecast) == 12)
        results.check("Dashboard has required keys",
                      all(k in dashboard for k in ['dso','burn_rate','runway_months','cash_conversion_cycle']),
                      f"missing keys: {[k for k in ['dso','burn_rate','runway_months','cash_conversion_cycle'] if k not in dashboard]}")
    except Exception as e:
        results.check("Full scenario exception", False, str(e))
    
    return results


def main():
    print("=" * 60)
    print("CASH FLOW MODEL - Formula Validation Suite")
    print("=" * 60)
    
    all_results = []
    all_results.append(test_dso())
    all_results.append(test_dpo())
    all_results.append(test_dio())
    all_results.append(test_ccc())
    all_results.append(test_burn_rate())
    all_results.append(test_runway())
    all_results.append(test_collection_probability())
    all_results.append(test_tax_estimation())
    all_results.append(test_milestone_deduplication())
    all_results.append(test_sales_tax())
    all_results.append(test_monte_carlo())
    all_results.append(test_stripe_connector())
    all_results.append(test_quickbooks_connector())
    all_results.append(test_load_from_connector())
    all_results.append(test_edge_cases())
    all_results.append(test_full_scenario())
    
    total_pass = sum(r.passed for r in all_results)
    total_fail = sum(r.failed for r in all_results)
    total = total_pass + total_fail
    
    print(f"\n{'='*60}")
    print(f"TOTAL: {total_pass}/{total} passed, {total_fail} failed")
    
    if total_fail > 0:
        print(f"\nFAILED TESTS:")
        for r in all_results:
            for e in r.errors:
                print(f"  - {e}")
        sys.exit(1)
    else:
        print("ALL TESTS PASSED")
        sys.exit(0)


if __name__ == '__main__':
    main()
