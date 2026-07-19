"""
Scenario Loader - Load cash flow models from multiple sources.
Supports JSON, CSV, Excel, and interactive CLI menu.

AUDIT COMPLIANT: All loaded data passes validation through model classes.
GENERALIZED: Works for any business type.
"""

import json
import csv
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from cash_flow_model import (
    CashFlowModel, Invoice, Expense, Project,
    PaymentStatus, ExpenseType
)


class ScenarioLoader:
    """Load cash flow scenarios from various sources."""
    
    # === JSON ===
    
    @staticmethod
    def load_from_json(filepath: str) -> CashFlowModel:
        """
        Load scenario from JSON file.
        
        JSON structure:
        {
            "name": "Scenario Name",
            "initial_balance": 75000,
            "dpo_days": 28,
            "dio_days": 0,
            "tax_rate": 0.25,
            "monthly_fixed_costs": {"rent": 3500, "salaries": 25000},
            "invoices": [...],
            "expenses": [...],
            "projects": [...]
        }
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return ScenarioLoader._build_model(data)
    
    @staticmethod
    def save_as_json(model: CashFlowModel, filepath: str, name: str = "Scenario"):
        """Export current model state to JSON."""
        data = {
            'name': name,
            'initial_balance': model.initial_balance,
            'dpo_days': model.dpo_days,
            'dio_days': model.dio_days,
            'tax_rate': model.tax_rate,
            'monthly_fixed_costs': model.monthly_fixed_costs,
            'invoices': [{
                'invoice_id': inv.invoice_id,
                'client': inv.client,
                'amount': inv.amount,
                'issue_date': inv.issue_date.isoformat(),
                'due_date': inv.due_date.isoformat(),
                'payment_terms_days': inv.payment_terms_days,
                'status': inv.status.value,
                'received_date': inv.received_date.isoformat() if inv.received_date else None,
                'received_amount': inv.received_amount
            } for inv in model.invoices],
            'expenses': [{
                'expense_id': exp.expense_id,
                'description': exp.description,
                'amount': exp.amount,
                'date': exp.date.isoformat(),
                'expense_type': exp.expense_type.value,
                'category': exp.category,
                'recurring': exp.recurring,
                'recurrence_months': exp.recurrence_months
            } for exp in model.expenses],
            'projects': [{
                'project_id': proj.project_id,
                'client': proj.client,
                'total_value': proj.total_value,
                'start_date': proj.start_date.isoformat(),
                'estimated_end_date': proj.estimated_end_date.isoformat(),
                'milestones': proj.milestones,
                'payments_received': proj.payments_received,
                'work_completion_pct': proj.work_completion_pct
            } for proj in model.projects]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"Scenario saved to {filepath}")
    
    # === CSV ===
    
    @staticmethod
    def load_from_csv(invoices_csv: str = None, expenses_csv: str = None,
                      projects_csv: str = None, config_csv: str = None) -> CashFlowModel:
        """
        Load scenario from CSV files.
        
        Files:
        - config.csv: initial_balance, dpo_days, dio_days, tax_rate
        - invoices.csv: invoice_id,client,amount,issue_date,due_date,payment_terms_days,status,received_date,received_amount
        - expenses.csv: expense_id,description,amount,date,expense_type,category,recurring
        - projects.csv: project_id,client,total_value,start_date,estimated_end_date,payments_received,work_completion_pct,milestones_json
        """
        # Load config or use defaults
        config = {'initial_balance': 0, 'dpo_days': 30, 'dio_days': 0, 'tax_rate': 0.25}
        if config_csv and os.path.exists(config_csv):
            with open(config_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    for k, v in row.items():
                        if k and v:
                            config[k.strip()] = float(v) if '.' in v else int(v)
        
        model = CashFlowModel(initial_balance=config.get('initial_balance', 0))
        model.set_dpo_days(config.get('dpo_days', 30))
        model.set_dio_days(config.get('dio_days', 0))
        model.set_tax_rate(config.get('tax_rate', 0.25))
        
        # Load invoices
        if invoices_csv and os.path.exists(invoices_csv):
            with open(invoices_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    model.add_invoice(Invoice(
                        invoice_id=row['invoice_id'],
                        client=row['client'],
                        amount=float(row['amount']),
                        issue_date=datetime.fromisoformat(row['issue_date']),
                        due_date=datetime.fromisoformat(row['due_date']),
                        payment_terms_days=int(row['payment_terms_days']),
                        status=PaymentStatus(row['status']),
                        received_date=datetime.fromisoformat(row['received_date']) if row.get('received_date') else None,
                        received_amount=float(row.get('received_amount', 0) or 0)
                    ))
        
        # Load expenses
        if expenses_csv and os.path.exists(expenses_csv):
            with open(expenses_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    model.add_expense(Expense(
                        expense_id=row['expense_id'],
                        description=row['description'],
                        amount=float(row['amount']),
                        date=datetime.fromisoformat(row['date']),
                        expense_type=ExpenseType(row['expense_type']),
                        category=row['category'],
                        recurring=row.get('recurring', 'false').lower() == 'true'
                    ))
        
        # Load projects
        if projects_csv and os.path.exists(projects_csv):
            with open(projects_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    milestones = json.loads(row.get('milestones_json', '[]') or '[]')
                    # Convert date strings to datetime objects
                    for ms in milestones:
                        if isinstance(ms.get('date'), str):
                            ms['date'] = datetime.fromisoformat(ms['date'])
                    model.add_project(Project(
                        project_id=row['project_id'],
                        client=row['client'],
                        total_value=float(row['total_value']),
                        start_date=datetime.fromisoformat(row['start_date']),
                        estimated_end_date=datetime.fromisoformat(row['estimated_end_date']),
                        milestones=milestones,
                        payments_received=float(row.get('payments_received', 0) or 0),
                        work_completion_pct=float(row.get('work_completion_pct', 0) or 0)
                    ))
        
        return model
    
    @staticmethod
    def save_as_csv(model: CashFlowModel, directory: str):
        """Export model to CSV files."""
        os.makedirs(directory, exist_ok=True)
        
        # Config
        with open(os.path.join(directory, 'config.csv'), 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['initial_balance', 'dpo_days', 'dio_days', 'tax_rate'])
            writer.writeheader()
            writer.writerow({
                'initial_balance': model.initial_balance,
                'dpo_days': model.dpo_days,
                'dio_days': model.dio_days,
                'tax_rate': model.tax_rate
            })
        
        # Invoices
        with open(os.path.join(directory, 'invoices.csv'), 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'invoice_id', 'client', 'amount', 'issue_date', 'due_date',
                'payment_terms_days', 'status', 'received_date', 'received_amount'
            ])
            writer.writeheader()
            for inv in model.invoices:
                writer.writerow({
                    'invoice_id': inv.invoice_id,
                    'client': inv.client,
                    'amount': inv.amount,
                    'issue_date': inv.issue_date.isoformat(),
                    'due_date': inv.due_date.isoformat(),
                    'payment_terms_days': inv.payment_terms_days,
                    'status': inv.status.value,
                    'received_date': inv.received_date.isoformat() if inv.received_date else '',
                    'received_amount': inv.received_amount
                })
        
        # Expenses
        with open(os.path.join(directory, 'expenses.csv'), 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'expense_id', 'description', 'amount', 'date',
                'expense_type', 'category', 'recurring'
            ])
            writer.writeheader()
            for exp in model.expenses:
                writer.writerow({
                    'expense_id': exp.expense_id,
                    'description': exp.description,
                    'amount': exp.amount,
                    'date': exp.date.isoformat(),
                    'expense_type': exp.expense_type.value,
                    'category': exp.category,
                    'recurring': exp.recurring
                })
        
        # Projects
        with open(os.path.join(directory, 'projects.csv'), 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'project_id', 'client', 'total_value', 'start_date',
                'estimated_end_date', 'payments_received', 'work_completion_pct', 'milestones_json'
            ])
            writer.writeheader()
            for proj in model.projects:
                writer.writerow({
                    'project_id': proj.project_id,
                    'client': proj.client,
                    'total_value': proj.total_value,
                    'start_date': proj.start_date.isoformat(),
                    'estimated_end_date': proj.estimated_end_date.isoformat(),
                    'payments_received': proj.payments_received,
                    'work_completion_pct': proj.work_completion_pct,
                    'milestones_json': json.dumps(proj.milestones)
                })
        
        print(f"CSV files saved to {directory}/")
    
    # === EXCEL ===
    
    @staticmethod
    def load_from_excel(filepath: str) -> CashFlowModel:
        """
        Load scenario from Excel file with sheets:
        - Config: initial_balance, dpo_days, dio_days, tax_rate
        - Invoices: invoice_id, client, amount, issue_date, due_date, ...
        - Expenses: expense_id, description, amount, date, expense_type, ...
        - Projects: project_id, client, total_value, start_date, ...
        """
        import pandas as pd
        
        xls = pd.ExcelFile(filepath)
        
        # Config
        config = {'initial_balance': 0, 'dpo_days': 30, 'dio_days': 0, 'tax_rate': 0.25}
        if 'Config' in xls.sheet_names:
            df = pd.read_excel(filepath, sheet_name='Config')
            for _, row in df.iterrows():
                key = str(row.iloc[0]).strip()
                val = row.iloc[1]
                if key in config:
                    config[key] = float(val)
        
        model = CashFlowModel(initial_balance=config['initial_balance'])
        model.set_dpo_days(int(config['dpo_days']))
        model.set_dio_days(int(config['dio_days']))
        model.set_tax_rate(config['tax_rate'])
        
        # Invoices
        if 'Invoices' in xls.sheet_names:
            df = pd.read_excel(filepath, sheet_name='Invoices')
            for _, row in df.iterrows():
                received_date = None
                if pd.notna(row.get('received_date')):
                    received_date = pd.to_datetime(row['received_date']).to_pydatetime()
                
                model.add_invoice(Invoice(
                    invoice_id=str(row['invoice_id']),
                    client=str(row['client']),
                    amount=float(row['amount']),
                    issue_date=pd.to_datetime(row['issue_date']).to_pydatetime(),
                    due_date=pd.to_datetime(row['due_date']).to_pydatetime(),
                    payment_terms_days=int(row['payment_terms_days']),
                    status=PaymentStatus(str(row['status'])),
                    received_date=received_date,
                    received_amount=float(row.get('received_amount', 0) or 0)
                ))
        
        # Expenses
        if 'Expenses' in xls.sheet_names:
            df = pd.read_excel(filepath, sheet_name='Expenses')
            for _, row in df.iterrows():
                model.add_expense(Expense(
                    expense_id=str(row['expense_id']),
                    description=str(row['description']),
                    amount=float(row['amount']),
                    date=pd.to_datetime(row['date']).to_pydatetime(),
                    expense_type=ExpenseType(str(row['expense_type'])),
                    category=str(row['category']),
                    recurring=str(row.get('recurring', 'false')).lower() == 'true'
                ))
        
        # Projects
        if 'Projects' in xls.sheet_names:
            df = pd.read_excel(filepath, sheet_name='Projects')
            for _, row in df.iterrows():
                milestones = []
                if pd.notna(row.get('milestones_json')):
                    milestones = json.loads(str(row['milestones_json']))
                
                model.add_project(Project(
                    project_id=str(row['project_id']),
                    client=str(row['client']),
                    total_value=float(row['total_value']),
                    start_date=pd.to_datetime(row['start_date']).to_pydatetime(),
                    estimated_end_date=pd.to_datetime(row['estimated_end_date']).to_pydatetime(),
                    milestones=milestones,
                    payments_received=float(row.get('payments_received', 0) or 0),
                    work_completion_pct=float(row.get('work_completion_pct', 0) or 0)
                ))
        
        return model
    
    # === CLI INTERACTIVE MENU ===
    
    @staticmethod
    def create_interactive() -> CashFlowModel:
        """Interactive CLI menu to create a scenario step by step."""
        print("\n" + "=" * 60)
        print("NEW SCENARIO - Interactive Setup")
        print("=" * 60)
        
        # Basic config
        print("\n[1/5] BASIC CONFIGURATION")
        print("-" * 40)
        
        initial_balance = ScenarioLoader._input_float("Initial cash balance ($)", 0)
        dpo_days = ScenarioLoader._input_int("Days Payable Outstanding (DPO)", 30)
        dio_days = ScenarioLoader._input_int("Days Inventory Outstanding (DIO, 0 for services)", 0)
        tax_rate = ScenarioLoader._input_float("Tax rate (e.g., 0.25 for 25%)", 0.25)
        
        model = CashFlowModel(initial_balance=initial_balance)
        model.set_dpo_days(dpo_days)
        model.set_dio_days(dio_days)
        model.set_tax_rate(tax_rate)
        
        # Fixed costs
        print("\n[2/5] MONTHLY FIXED COSTS")
        print("-" * 40)
        print("Enter each cost (empty name to finish):")
        
        fixed_costs = {}
        while True:
            name = input("  Cost name (or empty to finish): ").strip()
            if not name:
                break
            amount = ScenarioLoader._input_float(f"  Amount for '{name}'", 0)
            if amount > 0:
                fixed_costs[name] = amount
        
        if fixed_costs:
            model.set_monthly_fixed_costs(fixed_costs)
        
        # Invoices
        print("\n[3/5] INVOICES")
        print("-" * 40)
        print("Enter invoices (empty ID to finish):")
        
        today = datetime.now()
        inv_count = 0
        while True:
            invoice_id = input("  Invoice ID (or empty to finish): ").strip()
            if not invoice_id:
                break
            
            client = input("  Client name: ").strip() or "Unknown"
            amount = ScenarioLoader._input_float("  Amount ($)", 0)
            issue_days_ago = ScenarioLoader._input_int("  Issue date (days ago)", 0)
            payment_terms = ScenarioLoader._input_int("  Payment terms (days)", 30)
            
            status_str = input("  Status (pending/received/late/defaulted) [pending]: ").strip() or "pending"
            status = PaymentStatus(status_str)
            
            received_amount = 0
            received_date = None
            if status == PaymentStatus.RECEIVED:
                received_amount = ScenarioLoader._input_float("  Received amount ($)", amount)
                received_days_ago = ScenarioLoader._input_int("  Received date (days ago)", 0)
                received_date = today - timedelta(days=received_days_ago)
            
            issue_date = today - timedelta(days=issue_days_ago)
            due_date = issue_date + timedelta(days=payment_terms)
            
            model.add_invoice(Invoice(
                invoice_id=invoice_id,
                client=client,
                amount=amount,
                issue_date=issue_date,
                due_date=due_date,
                payment_terms_days=payment_terms,
                status=status,
                received_date=received_date,
                received_amount=received_amount
            ))
            inv_count += 1
            print(f"  [+] Invoice {invoice_id} added")
        
        # Expenses
        print("\n[4/5] EXPENSES")
        print("-" * 40)
        print("Enter expenses (empty ID to finish):")
        
        exp_count = 0
        while True:
            expense_id = input("  Expense ID (or empty to finish): ").strip()
            if not expense_id:
                break
            
            description = input("  Description: ").strip() or "Expense"
            amount = ScenarioLoader._input_float("  Amount ($)", 0)
            days_ago = ScenarioLoader._input_int("  Date (days ago)", 0)
            
            exp_type_str = input("  Type (fixed/variable/one_time/tax) [variable]: ").strip() or "variable"
            exp_type = ExpenseType(exp_type_str)
            
            category = input("  Category: ").strip() or "General"
            recurring = input("  Recurring? (y/n) [n]: ").strip().lower() == 'y'
            
            model.add_expense(Expense(
                expense_id=expense_id,
                description=description,
                amount=amount,
                date=today - timedelta(days=days_ago),
                expense_type=exp_type,
                category=category,
                recurring=recurring
            ))
            exp_count += 1
            print(f"  [+] Expense {expense_id} added")
        
        # Projects
        print("\n[5/5] PROJECTS")
        print("-" * 40)
        print("Enter projects (empty ID to finish):")
        
        proj_count = 0
        while True:
            project_id = input("  Project ID (or empty to finish): ").strip()
            if not project_id:
                break
            
            client = input("  Client name: ").strip() or "Unknown"
            total_value = ScenarioLoader._input_float("  Total project value ($)", 0)
            start_days_ago = ScenarioLoader._input_int("  Start date (days ago)", 0)
            end_days_ahead = ScenarioLoader._input_int("  End date (days from now)", 30)
            work_pct = ScenarioLoader._input_float("  Work completion %", 0)
            payments_received = ScenarioLoader._input_float("  Payments received ($)", 0)
            
            # Milestones
            milestones = []
            print("  Enter milestones (empty name to finish):")
            while True:
                ms_name = input("    Milestone name (or empty to finish): ").strip()
                if not ms_name:
                    break
                ms_amount = ScenarioLoader._input_float(f"    Amount for '{ms_name}'", 0)
                ms_days = ScenarioLoader._input_int(f"    Days from now for '{ms_name}'", 30)
                
                milestones.append({
                    'name': ms_name,
                    'amount': ms_amount,
                    'date': today + timedelta(days=ms_days),
                    'paid': False
                })
                print(f"    [+] Milestone '{ms_name}' added")
            
            model.add_project(Project(
                project_id=project_id,
                client=client,
                total_value=total_value,
                start_date=today - timedelta(days=start_days_ago),
                estimated_end_date=today + timedelta(days=end_days_ahead),
                milestones=milestones,
                payments_received=payments_received,
                work_completion_pct=work_pct
            ))
            proj_count += 1
            print(f"  [+] Project {project_id} added")
        
        # Summary
        print("\n" + "=" * 60)
        print("SCENARIO CREATED")
        print("=" * 60)
        print(f"  Invoices: {inv_count}")
        print(f"  Expenses: {exp_count}")
        print(f"  Projects: {proj_count}")
        print(f"  Fixed costs: ${sum(fixed_costs.values()):,.2f}/month")
        print(f"  Balance: ${initial_balance:,.2f}")
        print("=" * 60)
        
        return model
    
    # === TEMPLATE GENERATOR ===
    
    @staticmethod
    def generate_templates(directory: str):
        """Generate example template files for CSV and JSON."""
        os.makedirs(directory, exist_ok=True)
        
        # JSON template
        json_template = {
            "name": "My Business Scenario",
            "initial_balance": 75000,
            "dpo_days": 30,
            "dio_days": 0,
            "tax_rate": 0.25,
            "monthly_fixed_costs": {
                "rent": 3500,
                "salaries": 25000,
                "utilities": 500
            },
            "invoices": [
                {
                    "invoice_id": "INV-001",
                    "client": "Client A",
                    "amount": 25000,
                    "issue_date": "2026-01-01",
                    "due_date": "2026-01-31",
                    "payment_terms_days": 30,
                    "status": "pending",
                    "received_date": None,
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
                    "recurring": True
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
                        {"name": "Phase 1", "amount": 30000, "date": "2026-03-01", "paid": False},
                        {"name": "Phase 2", "amount": 50000, "date": "2026-06-01", "paid": False}
                    ],
                    "payments_received": 0,
                    "work_completion_pct": 25.0
                }
            ]
        }
        
        with open(os.path.join(directory, 'scenario_template.json'), 'w', encoding='utf-8') as f:
            json.dump(json_template, f, indent=2, ensure_ascii=False)
        
        # CSV templates
        with open(os.path.join(directory, 'config_template.csv'), 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['initial_balance', 'dpo_days', 'dio_days', 'tax_rate'])
            writer.writerow([75000, 30, 0, 0.25])
        
        with open(os.path.join(directory, 'invoices_template.csv'), 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['invoice_id', 'client', 'amount', 'issue_date', 'due_date',
                           'payment_terms_days', 'status', 'received_date', 'received_amount'])
            writer.writerow(['INV-001', 'Client A', 25000, '2026-01-01', '2026-01-31',
                           30, 'pending', '', 0])
            writer.writerow(['INV-002', 'Client B', 15000, '2025-12-01', '2025-12-31',
                           30, 'received', '2025-12-28', 15000])
        
        with open(os.path.join(directory, 'expenses_template.csv'), 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['expense_id', 'description', 'amount', 'date',
                           'expense_type', 'category', 'recurring'])
            writer.writerow(['EXP-001', 'Cloud hosting', 500, '2026-01-15',
                           'variable', 'Infrastructure', 'true'])
            writer.writerow(['EXP-002', 'Legal review', 2000, '2026-01-10',
                           'one_time', 'Legal', 'false'])
        
        with open(os.path.join(directory, 'projects_template.csv'), 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['project_id', 'client', 'total_value', 'start_date',
                           'estimated_end_date', 'payments_received', 'work_completion_pct', 'milestones_json'])
            milestones = json.dumps([
                {"name": "Phase 1", "amount": 30000, "date": "2026-03-01", "paid": False},
                {"name": "Phase 2", "amount": 50000, "date": "2026-06-01", "paid": False}
            ])
            writer.writerow(['PRJ-001', 'Client A', 80000, '2026-01-01',
                           '2026-06-30', 0, 25.0, milestones])
        
        print(f"Templates generated in {directory}/")
        print("Files:")
        print("  - scenario_template.json")
        print("  - config_template.csv")
        print("  - invoices_template.csv")
        print("  - expenses_template.csv")
        print("  - projects_template.csv")
    
    # === HELPER METHODS ===
    
    @staticmethod
    def _build_model(data: dict) -> CashFlowModel:
        """Build model from dictionary data."""
        model = CashFlowModel(initial_balance=data.get('initial_balance', 0))
        model.set_dpo_days(data.get('dpo_days', 30))
        model.set_dio_days(data.get('dio_days', 0))
        model.set_tax_rate(data.get('tax_rate', 0.25))
        
        # Fixed costs
        if 'monthly_fixed_costs' in data:
            model.set_monthly_fixed_costs(data['monthly_fixed_costs'])
        
        # Invoices
        for inv_data in data.get('invoices', []):
            received_date = None
            if inv_data.get('received_date'):
                received_date = datetime.fromisoformat(inv_data['received_date'])
            
            model.add_invoice(Invoice(
                invoice_id=inv_data['invoice_id'],
                client=inv_data['client'],
                amount=inv_data['amount'],
                issue_date=datetime.fromisoformat(inv_data['issue_date']),
                due_date=datetime.fromisoformat(inv_data['due_date']),
                payment_terms_days=inv_data.get('payment_terms_days', 30),
                status=PaymentStatus(inv_data.get('status', 'pending')),
                received_date=received_date,
                received_amount=inv_data.get('received_amount', 0)
            ))
        
        # Expenses
        for exp_data in data.get('expenses', []):
            model.add_expense(Expense(
                expense_id=exp_data['expense_id'],
                description=exp_data['description'],
                amount=exp_data['amount'],
                date=datetime.fromisoformat(exp_data['date']),
                expense_type=ExpenseType(exp_data.get('expense_type', 'variable')),
                category=exp_data.get('category', 'General'),
                recurring=exp_data.get('recurring', False)
            ))
        
        # Projects
        for proj_data in data.get('projects', []):
            milestones = proj_data.get('milestones', [])
            # Convert date strings in milestones
            for ms in milestones:
                if isinstance(ms.get('date'), str):
                    ms['date'] = datetime.fromisoformat(ms['date'])
            
            model.add_project(Project(
                project_id=proj_data['project_id'],
                client=proj_data['client'],
                total_value=proj_data['total_value'],
                start_date=datetime.fromisoformat(proj_data['start_date']),
                estimated_end_date=datetime.fromisoformat(proj_data['estimated_end_date']),
                milestones=milestones,
                payments_received=proj_data.get('payments_received', 0),
                work_completion_pct=proj_data.get('work_completion_pct', 0)
            ))
        
        return model
    
    @staticmethod
    def _input_float(prompt: str, default: float) -> float:
        """Get float input with default."""
        while True:
            try:
                val = input(f"  {prompt} [{default}]: ").strip()
                if not val:
                    return default
                return float(val)
            except ValueError:
                print("  [!] Invalid number, try again")
    
    @staticmethod
    def _input_int(prompt: str, default: int) -> int:
        """Get int input with default."""
        while True:
            try:
                val = input(f"  {prompt} [{default}]: ").strip()
                if not val:
                    return default
                return int(val)
            except ValueError:
                print("  [!] Invalid integer, try again")
