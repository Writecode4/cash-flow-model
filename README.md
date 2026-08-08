# Cash Flow Model for Data Consulting Firms

Advanced cash flow forecasting and scenario planning tool designed specifically for data consulting businesses.

## Features

- **Cash Conversion Cycle Analysis** - Track how quickly you convert work into cash
- **Scenario Planning** - Test what-if scenarios (new clients, delays, hires)
- **Monte Carlo Simulation** - Probabilistic forecast with P10/P50/P90 ranges, survival probability and collection-risk (payment delay + bad debt) distributions
- **Sales Tax (VAT/IVA) Awareness** - Configurable sales tax rate; liabilities are reserved from the balance so Runway uses *available* cash, not the full bank balance
- **API Connectors** - Import real invoices, payments and expenses from **Stripe** and **QuickBooks Online**
- **Liquidity Stress Testing** - See how your business survives under different conditions
- **Client Payment Behavior** - Identify slow payers and patterns
- **Project-Level Tracking** - Monitor cash flow per project/milestone
- **Excel Export** - Generate reports for stakeholders

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the example
python run_example.py

# Run the test suite (94 checks)
python test_suite.py
```

## Usage

```python
from cash_flow_model import CashFlowModel, Invoice, Project
from datetime import datetime, timedelta

# Create model with initial balance
model = CashFlowModel(initial_balance=50000)

# Set monthly fixed costs
model.set_monthly_fixed_costs({
    'rent': 2500,
    'salaries': 15000,
    'tools': 800
})

# Add invoices
model.add_invoice(Invoice(
    invoice_id='INV-001',
    client='Tech Corp',
    amount=25000,
    issue_date=datetime.now(),
    due_date=datetime.now() + timedelta(days=30),
    payment_terms_days=30
))

# Add projects with milestones
model.add_project(Project(
    project_id='PRJ-001',
    client='Enterprise Inc',
    total_value=100000,
    start_date=datetime.now(),
    estimated_end_date=datetime.now() + timedelta(days=90),
    milestones=[
        {'name': 'Phase 1', 'amount': 30000, 'date': datetime.now() + timedelta(days=30)},
        {'name': 'Phase 2', 'amount': 70000, 'date': datetime.now() + timedelta(days=90)}
    ]
))

# Run analysis
dashboard = model.generate_dashboard_data()
print(f"Runway: {dashboard['runway_months']:.1f} months")
print(f"Available cash: ${dashboard['available_cash']:,.2f}")  # balance - sales tax liability

# Configure sales tax (e.g. 21% IVA)
model.set_sales_tax_rate(0.21)

# Scenario analysis
scenarios = {
    'Base': {},
    'Growth': {'income_multiplier': 1.3},
    'Downturn': {'income_multiplier': 0.7}
}
results = model.scenario_analysis(scenarios)

# Monte Carlo simulation (probabilistic, P10/P50/P90)
mc = model.monte_carlo(
    n_simulations=1000, months=12, seed=42,
    income_volatility=0.15, expense_volatility=0.10,
    payment_delay_mean_days=10, bad_debt_probability=0.05
)
print(f"Survival probability: {mc['survival_probability']*100:.1f}%")
print(mc['percentiles'])

# Export to Excel
model.export_to_excel('report.xlsx')
```

## Key Metrics Explained

| Metric | What it Means | Target |
|--------|---------------|--------|
| **DSO** (Days Sales Outstanding) | Avg days to collect payment | < 30 days |
| **Cash Conversion Cycle** | Time from work to cash in bank | < 45 days |
| **Burn Rate** | Monthly cash outflow | Track trend |
| **Runway** | Months until cash runs out | > 6 months |

## Scenario Planning

Test different business situations:

```python
scenarios = {
    'Win Big Contract': {'income_multiplier': 1.3},
    'Client Defaults': {'income_multiplier': 0.8},
    'Slow Payments': {'payment_delay_days': 20},
    'Hire Employee': {'new_monthly_cost': 5000},
    'Best Case': {'income_multiplier': 1.3, 'expense_multiplier': 0.9}
}
```

## API Connectors

Import real data from your billing/accounting tools instead of typing dictionaries by hand.

```python
from connectors.stripe import StripeConnector
from connectors.quickbooks import QuickBooksConnector
from scenario_loader import ScenarioLoader

# --- Stripe (live) ---
connector = StripeConnector(api_key='sk_live_...')
model = ScenarioLoader.load_from_connector(
    connector,
    config={'initial_balance': 50000, 'sales_tax_rate': 0.21}
)

# --- QuickBooks Online (live) ---
qb = QuickBooksConnector(access_token='OAuth2_token', realm_id='123456789')
model = ScenarioLoader.load_from_connector(qb)

# --- Offline / testable: feed raw payloads directly ---
payload = {
    'invoices': [
        {'id': 'in_1', 'customer_name': 'Acme', 'status': 'paid',
         'created': 1750000000, 'due_date': 1752600000, 'total': 2500000},
        {'id': 'in_2', 'customer_email': 'b@x.com', 'status': 'open',
         'created': 1750000000, 'amount_due': 100000},
    ],
    'payments': [],
    'expenses': [],
}
model = ScenarioLoader.load_from_connector(StripeConnector(), data=payload)

dashboard = model.generate_dashboard_data()
print(f"Available cash: ${dashboard['available_cash']:,.2f}")
```

- Stripe amounts are received in **cents** and converted to major units automatically.
- Stripe status mapping: `paid` → RECEIVED, `open` → PENDING, `past_due` → LATE,
  `uncollectible` → DEFAULTED, `draft`/`void` → skipped.
- QuickBooks status is derived from `Balance`/`DueDate` (or an explicit `status` field).
- **Optional dependencies**: `pip install stripe requests`. Live `fetch()` requires
  real credentials; parsing and `to_model()` work offline with plain dicts.

## Visualization

```python
from dashboard import CashFlowDashboard

dashboard = CashFlowDashboard(model)
dashboard.create_full_dashboard(save_path='dashboard.png')

# Monte Carlo band chart (P10-P90 with survival stats)
dashboard.plot_monte_carlo(save_path='monte_carlo.png')
```

## File Structure

```
cash-flow-model/
├── cash_flow_model.py    # Core model classes
├── dashboard.py          # Visualization module
├── scenario_loader.py    # Load/save JSON, CSV, Excel + API connectors
├── connectors/           # API connectors (Stripe, QuickBooks)
├── sample_data.py        # Example data for different firm stages
├── test_suite.py         # Formula + connector test suite
├── run_example.py        # Demo script
├── requirements.txt      # Dependencies
└── README.md            # This file
```

## Consulting Firm Scenarios Included

1. **Startup Phase** - First 6 months, building pipeline
2. **Realistic Mid-Size** - 3-person team, multiple projects
3. **Growth Phase** - 10+ employees, scaling operations

Each scenario includes realistic invoices, expenses, and project data.

## Limitations (read before using for real decisions)

This is a **cash-basis forecasting sandbox**, not an audited financial model. It is
useful as a short-term (2-3 month) operational simulator and as a portfolio / MVP,
but it does **not** replace professional FP&A. Known gaps:

- **No accrual accounting**: revenue recognition, accrued liabilities (vacation,
  bonuses, deferred tax) and cost-of-delivery margins per project are not modeled.
- **Sales tax is reserved but not a full tax engine**: VAT/IVA is deducted from
  available cash, but withholding taxes (e.g. IRPF), corporate tax timing and
  e-invoicing (Verifactu, etc.) must be validated against your local rules.
- **Fixed scenario multipliers are sensitivity knobs, not business scenarios**.
  Use `monte_carlo()` for probabilistic ranges (P10/P50/P90).
- **No financing** (debt/equity, credit lines), no CAPEX/depreciation, no owner
  distributions.
- **API connectors cover invoices/payments/expenses** (Stripe, QuickBooks Online)
  but do not cover bank feeds (PSD2) or every accounting product yet; always
  validate the imported payload before relying on it.

Use the *deterministic* output as an early-warning signal, and the *Monte Carlo*
ranges to size risk — but for board-level or investor decisions, run a proper
three-statement model with a qualified controller.
