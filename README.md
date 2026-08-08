# Cash Flow Model for Data Consulting Firms

Advanced cash flow forecasting and scenario planning tool designed specifically for data consulting businesses.

## Features

- **Cash Conversion Cycle Analysis** - Track how quickly you convert work into cash
- **Scenario Planning** - Test what-if scenarios (new clients, delays, hires)
- **Monte Carlo Simulation** - Probabilistic forecast with P10/P50/P90 ranges, survival probability and collection-risk (payment delay + bad debt) distributions
- **Sales Tax (VAT/IVA) Awareness** - Configurable sales tax rate; liabilities are reserved from the balance so Runway uses *available* cash, not the full bank balance
- **API Connectors** - Import real invoices, payments and expenses from **Stripe** and **QuickBooks Online**
- **CSV / Excel / JSON Import** - Load your own data from files with generated templates and a documented schema
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

## Importing Your Own Data (CSV / Excel / JSON)

If you don't use Stripe or QuickBooks, load your real data from files. The
`examples/` folder ships ready-made templates — fill them in and load.

### Step 1 — Generate the templates

```bash
python load_scenario.py --templates examples
```

This creates `examples/config_template.csv`, `invoices_template.csv`,
`expenses_template.csv`, `projects_template.csv` and `scenario_template.json`.

### Step 2 — Fill in the files

**`config.csv`** (single row, the other files can be left empty):

| Column | Type | Example | Notes |
|--------|------|---------|-------|
| `initial_balance` | number | `75000` | Opening cash balance |
| `dpo_days` | int | `30` | Days payable outstanding |
| `dio_days` | int | `0` | Days inventory (0 for services) |
| `tax_rate` | number | `0.25` | Corporate tax rate (0-1) |
| `sales_tax_rate` | number | `0.21` | Sales tax / VAT collected on income, settled quarterly (0 = none) |

**`invoices.csv`**:

| Column | Type | Example | Notes |
|--------|------|---------|-------|
| `invoice_id` | text | `INV-001` | Unique |
| `client` | text | `Tech Corp` | |
| `amount` | number | `25000` | > 0 |
| `issue_date` | date | `2026-01-01` | ISO format `YYYY-MM-DD` |
| `due_date` | date | `2026-01-31` | Must be >= issue_date |
| `payment_terms_days` | int | `30` | |
| `status` | enum | `pending` | `pending` / `received` / `late` / `defaulted` |
| `received_date` | date (empty) | `2026-01-28` | Required if status = received |
| `received_amount` | number | `25000` | Paid amount (<= amount) |

**`expenses.csv`**:

| Column | Type | Example | Notes |
|--------|------|---------|-------|
| `expense_id` | text | `EXP-001` | Unique |
| `description` | text | `Cloud hosting` | |
| `amount` | number | `500` | > 0 |
| `date` | date | `2026-01-15` | ISO format |
| `expense_type` | enum | `variable` | `fixed` / `variable` / `one_time` / `tax` |
| `category` | text | `Infrastructure` | |
| `recurring` | bool | `true` | `true` / `false` — recurring expenses count toward burn rate |

**`projects.csv`**:

| Column | Type | Example | Notes |
|--------|------|---------|-------|
| `project_id` | text | `PRJ-001` | Unique |
| `client` | text | `Client A` | |
| `total_value` | number | `80000` | > 0 |
| `start_date` | date | `2026-01-01` | ISO format |
| `estimated_end_date` | date | `2026-06-30` | |
| `payments_received` | number | `0` | <= total_value |
| `work_completion_pct` | number | `25.0` | 0-100 |
| `milestones_json` | JSON text | `[{"name": "Phase 1", "amount": 30000, "date": "2026-03-01", "paid": false}]` | Array of milestone dicts |

### Step 3 — Load and analyze

```bash
# CLI: load the CSV folder, run analysis and export report.xlsx
python load_scenario.py --csv examples

# CLI: load a single JSON or Excel file
python load_scenario.py my_company.json
python load_scenario.py my_company.xlsx
```

Or from code:

```python
from scenario_loader import ScenarioLoader

# CSV
model = ScenarioLoader.load_from_csv(
    config_csv='examples/config_template.csv',
    invoices_csv='examples/invoices_template.csv',
    expenses_csv='examples/expenses_template.csv',
    projects_csv='examples/projects_template.csv',
)

# Excel — sheets: Config, Invoices, Expenses, Projects (same columns as the CSVs)
model = ScenarioLoader.load_from_excel('my_company.xlsx')

# JSON
model = ScenarioLoader.load_from_json('scenario_template.json')
```

Once loaded, the model behaves exactly like the sample models:

```python
dashboard = model.generate_dashboard_data()
mc = model.monte_carlo(n_simulations=1000, months=12, seed=42,
                       payment_delay_mean_days=10, bad_debt_probability=0.05)
model.export_to_excel('my_report.xlsx')
```

### JSON format

`scenario_template.json` is the schema the loader expects. Every field except
the optional ones below must be present:

```json
{
  "name": "My Business Scenario",
  "initial_balance": 75000,
  "dpo_days": 30,
  "dio_days": 0,
  "tax_rate": 0.25,
  "sales_tax_rate": 0.21,
  "monthly_fixed_costs": {"rent": 3500, "salaries": 25000},
  "invoices": [
    {
      "invoice_id": "INV-001",
      "client": "Tech Corp",
      "amount": 25000,
      "issue_date": "2026-01-15",
      "due_date": "2026-02-15",
      "payment_terms_days": 30,
      "status": "pending",
      "received_date": null,
      "received_amount": 0
    }
  ],
  "expenses": [
    {
      "expense_id": "EXP-001",
      "description": "Cloud hosting",
      "amount": 500,
      "date": "2026-01-15",
      "expense_type": "variable",
      "category": "Infrastructure",
      "recurring": true
    }
  ],
  "projects": [
    {
      "project_id": "PRJ-001",
      "client": "Client A",
      "total_value": 80000,
      "start_date": "2026-01-01",
      "estimated_end_date": "2026-06-30",
      "milestones": [
        {"name": "Phase 1", "amount": 30000, "date": "2026-03-01", "paid": false}
      ],
      "payments_received": 0,
      "work_completion_pct": 25.0
    }
  ]
}
```

Field reference:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `initial_balance` | number | yes | Opening cash balance |
| `dpo_days` | int | yes | Days payable outstanding |
| `dio_days` | int | yes | Days inventory (0 for services) |
| `tax_rate` | number | yes | Corporate tax rate (0-1) |
| `sales_tax_rate` | number | no | Sales tax / VAT rate (default 0) |
| `monthly_fixed_costs` | object | no | Name → monthly amount |
| `invoices[].invoice_id` | text | yes | Unique |
| `invoices[].client` | text | yes | |
| `invoices[].amount` | number | yes | > 0 |
| `invoices[].issue_date` | date | yes | ISO `YYYY-MM-DD` |
| `invoices[].due_date` | date | yes | >= issue_date |
| `invoices[].payment_terms_days` | int | yes | |
| `invoices[].status` | enum | yes | `pending` / `received` / `late` / `defaulted` |
| `invoices[].received_date` | date | no | Required if status = received |
| `invoices[].received_amount` | number | no | Paid amount (<= amount) |
| `expenses[].expense_id` | text | yes | Unique |
| `expenses[].description` | text | yes | |
| `expenses[].amount` | number | yes | > 0 |
| `expenses[].date` | date | yes | ISO format |
| `expenses[].expense_type` | enum | yes | `fixed` / `variable` / `one_time` / `tax` |
| `expenses[].category` | text | no | Defaults to `General` |
| `expenses[].recurring` | bool | no | Recurring expenses count toward burn rate |
| `projects[].project_id` | text | yes | Unique |
| `projects[].client` | text | yes | |
| `projects[].total_value` | number | yes | > 0 |
| `projects[].start_date` | date | yes | ISO format |
| `projects[].estimated_end_date` | date | yes | |
| `projects[].milestones[]` | object[] | no | `name`, `amount`, `date`, `paid` |
| `projects[].payments_received` | number | no | <= total_value |
| `projects[].work_completion_pct` | number | no | 0-100 |

The same schema maps 1:1 to the CSV columns and Excel sheets described above, so
a consultant can export from any tool (Stripe, QuickBooks, Xero, Holded, Sage, or
even a manual spreadsheet), reshape into this format, and load it in minutes.

**Tip:** start from `--templates`, keep one invoice per row, and leave unused
files empty. If a value fails validation (e.g. negative amount or `received_date`
missing on a `received` invoice), the loader raises an error telling you exactly
what is wrong.

## API Connectors

The connectors live in `connectors/` and are fully implemented: `StripeConnector`
and `QuickBooksConnector`. They turn raw billing/accounting records into a
validated `CashFlowModel`, so you stop typing invoices by hand.

**Full live workflow (Stripe example):**

```python
from connectors.stripe import StripeConnector
from scenario_loader import ScenarioLoader

connector = StripeConnector(api_key='sk_live_...')          # or sk_test_...
model = ScenarioLoader.load_from_connector(
    connector,
    config={
        'initial_balance': 50000,
        'sales_tax_rate': 0.21,           # VAT/IVA
        'monthly_fixed_costs': {'rent': 2500, 'salaries': 15000},
    },
)
# model is now a normal CashFlowModel:
print(model.generate_dashboard_data()['available_cash'])
model.export_to_excel('stripe_report.xlsx')
```

**Same flow for QuickBooks Online** (OAuth2 token + realm ID):

```python
from connectors.quickbooks import QuickBooksConnector
qb = QuickBooksConnector(access_token='OAuth2_token', realm_id='123456789')
model = ScenarioLoader.load_from_connector(qb, config={'sales_tax_rate': 0.21})
```

**Offline / testable:** pass the raw payload directly — no network or keys needed.
Parsing and `to_model()` work with plain dicts in the connector's native shape:

```python
from connectors.stripe import StripeConnector
from scenario_loader import ScenarioLoader

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
```

**Supported `config` keys** (same for both connectors):

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `initial_balance` | float | 0 | Opening cash balance |
| `dpo_days` | int | 30 | Days payable outstanding |
| `dio_days` | int | 0 | Days inventory outstanding |
| `tax_rate` | float | 0.25 | Corporate/income tax rate |
| `sales_tax_rate` | float | 0.0 | Sales tax (VAT/IVA) rate |
| `monthly_fixed_costs` | dict | {} | Recurring monthly costs |

**Mapping rules:**
- **Stripe**: amounts are received in **cents** and converted to major units
  automatically. Status: `paid` → RECEIVED, `open` → PENDING, `past_due` → LATE,
  `uncollectible` → DEFAULTED, `draft`/`void` and `$0` invoices → skipped.
- **QuickBooks**: status derived from `Balance`/`DueDate` (or an explicit `status`
  field). `Balance = 0` → RECEIVED, overdue → LATE, future due → PENDING.
- **Optional dependencies**: `pip install stripe requests`. `fetch()` requires
  credentials and raises a clear `ConnectorError` otherwise; `to_model()` is
  always usable offline.

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
├── cash_flow_model.py    # Core model classes (cash flow, tax, Monte Carlo)
├── dashboard.py          # Matplotlib dashboards + Monte Carlo bands
├── scenario_loader.py    # Load/save JSON, CSV, Excel + API connector orchestration
├── load_scenario.py      # CLI: --templates, --csv, --interactive, JSON/Excel
├── generate_dashboard.py # Generates the interactive Chart.js dashboard.html
├── connectors/           # API connectors: stripe.py, quickbooks.py
├── sample_data.py        # Sample data for startup / mid-size / growth stages
├── test_suite.py         # Formula + connector test suite (94 checks)
├── run_example.py        # Demo script
├── index.html            # Standalone interactive HTML dashboard
├── interactive.html      # Standalone interactive HTML dashboard (alt)
├── examples/             # CSV/JSON templates (see "Importing Your Own Data")
├── netlify.toml          # Static hosting config
├── requirements.txt      # Dependencies (connectors optional, see below)
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
