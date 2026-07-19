# Cash Flow Model for Data Consulting Firms

Advanced cash flow forecasting and scenario planning tool designed specifically for data consulting businesses.

## Features

- **Cash Conversion Cycle Analysis** - Track how quickly you convert work into cash
- **Scenario Planning** - Test what-if scenarios (new clients, delays, hires)
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

# Scenario analysis
scenarios = {
    'Base': {},
    'Growth': {'income_multiplier': 1.3},
    'Downturn': {'income_multiplier': 0.7}
}
results = model.scenario_analysis(scenarios)

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

## Visualization

```python
from dashboard import CashFlowDashboard

dashboard = CashFlowDashboard(model)
dashboard.create_full_dashboard(save_path='dashboard.png')
```

## File Structure

```
cash-flow-model/
├── cash_flow_model.py    # Core model classes
├── dashboard.py          # Visualization module
├── sample_data.py        # Example data for different firm stages
├── run_example.py        # Demo script
├── requirements.txt      # Dependencies
└── README.md            # This file
```

## Consulting Firm Scenarios Included

1. **Startup Phase** - First 6 months, building pipeline
2. **Realistic Mid-Size** - 3-person team, multiple projects
3. **Growth Phase** - 10+ employees, scaling operations

Each scenario includes realistic invoices, expenses, and project data.
