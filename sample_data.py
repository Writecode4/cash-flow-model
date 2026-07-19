"""
Sample data for testing the cash flow model.
AUDIT COMPLIANT: Clean data, no inconsistencies.
GENERALIZED: Works for any business type.
"""

from datetime import datetime, timedelta
from cash_flow_model import (
    CashFlowModel, Invoice, Expense, Project,
    PaymentStatus, ExpenseType
)


def create_sample_model() -> CashFlowModel:
    """
    Create a sample model for a mid-size business.
    All data is consistent and audit-compliant.
    """
    model = CashFlowModel(initial_balance=75000)
    
    today = datetime.now()
    
    # Fixed monthly costs
    model.set_monthly_fixed_costs({
        'salaries': 25000,
        'rent': 3500,
        'tools_software': 1200,
        'cloud_infrastructure': 800,
        'insurance': 500,
        'marketing': 1000,
        'accounting_legal': 600,
        'miscellaneous': 500
    })
    
    # Configure DPO based on actual payment behavior
    model.set_dpo_days(28)
    
    # Configure tax rate
    model.set_tax_rate(0.25)
    
    # === PROJECTS ===
    # Milestones with paid=True ONLY if corresponding invoice exists
    
    model.add_project(Project(
        project_id='PRJ-001',
        client='Client A',
        total_value=85000,
        start_date=today - timedelta(days=45),
        estimated_end_date=today + timedelta(days=45),
        milestones=[
            {'name': 'Phase 1', 'amount': 25000, 
             'date': today + timedelta(days=15), 'paid': False},
            {'name': 'Phase 2', 'amount': 35000, 
             'date': today + timedelta(days=35), 'paid': False},
            {'name': 'Phase 3', 'amount': 25000, 
             'date': today + timedelta(days=50), 'paid': False}
        ],
        payments_received=0,
        work_completion_pct=35.0
    ))
    
    model.add_project(Project(
        project_id='PRJ-002',
        client='Client B',
        total_value=45000,
        start_date=today - timedelta(days=20),
        estimated_end_date=today + timedelta(days=40),
        milestones=[
            {'name': 'Delivery', 'amount': 45000, 
             'date': today + timedelta(days=40), 'paid': False}
        ],
        payments_received=0,
        work_completion_pct=20.0
    ))
    
    # === INVOICES ===
    # Only create invoices for work that has been billed
    
    # Pending invoices
    model.add_invoice(Invoice(
        invoice_id='INV-001',
        client='Client A',
        amount=25000,
        issue_date=today - timedelta(days=15),
        due_date=today + timedelta(days=15),
        payment_terms_days=30,
        status=PaymentStatus.PENDING
    ))
    
    model.add_invoice(Invoice(
        invoice_id='INV-002',
        client='Client B',
        amount=12000,
        issue_date=today - timedelta(days=10),
        due_date=today + timedelta(days=20),
        payment_terms_days=30,
        status=PaymentStatus.PENDING
    ))
    
    # Overdue invoice (low collection probability)
    model.add_invoice(Invoice(
        invoice_id='INV-003',
        client='Client C',
        amount=8500,
        issue_date=today - timedelta(days=75),
        due_date=today - timedelta(days=45),
        payment_terms_days=30,
        status=PaymentStatus.LATE,
        received_amount=0
    ))
    
    # Paid invoices (historical - for DSO calculation)
    model.add_invoice(Invoice(
        invoice_id='INV-004',
        client='Client D',
        amount=22000,
        issue_date=today - timedelta(days=45),
        due_date=today - timedelta(days=15),
        payment_terms_days=30,
        status=PaymentStatus.RECEIVED,
        received_date=today - timedelta(days=18),
        received_amount=22000
    ))
    
    model.add_invoice(Invoice(
        invoice_id='INV-005',
        client='Client A',
        amount=18000,
        issue_date=today - timedelta(days=60),
        due_date=today - timedelta(days=30),
        payment_terms_days=30,
        status=PaymentStatus.RECEIVED,
        received_date=today - timedelta(days=28),
        received_amount=18000
    ))
    
    model.add_invoice(Invoice(
        invoice_id='INV-006',
        client='Client E',
        amount=35000,
        issue_date=today - timedelta(days=75),
        due_date=today - timedelta(days=45),
        payment_terms_days=30,
        status=PaymentStatus.RECEIVED,
        received_date=today - timedelta(days=40),
        received_amount=35000
    ))
    
    # === EXPENSES ===
    # Recurring expenses properly marked for burn rate calculation
    
    expenses_data = [
        ('Cloud Services', 1450, 3, 'Infrastructure', ExpenseType.VARIABLE, True),
        ('Processing Costs', 890, 5, 'Infrastructure', ExpenseType.VARIABLE, True),
        ('Freelancer Payment', 4500, 7, 'Personnel', ExpenseType.VARIABLE, True),
        ('Client Event', 280, 2, 'Business Development', ExpenseType.VARIABLE, False),
        ('Subscriptions', 150, 10, 'Software', ExpenseType.VARIABLE, False),
        ('Conference', 1200, 15, 'Marketing', ExpenseType.ONE_TIME, False),
        ('Legal Review', 2000, 8, 'Legal', ExpenseType.ONE_TIME, False),
    ]
    
    for desc, amount, days_ago, category, exp_type, recurring in expenses_data:
        model.add_expense(Expense(
            expense_id=f'EXP-{len(model.expenses)+1:04d}',
            description=desc,
            amount=amount,
            date=today - timedelta(days=days_ago),
            expense_type=exp_type,
            category=category,
            recurring=recurring
        ))
    
    return model


def create_startup_model() -> CashFlowModel:
    """Model for a startup (first 6 months)."""
    model = CashFlowModel(initial_balance=30000)
    
    today = datetime.now()
    
    model.set_monthly_fixed_costs({
        'co_working': 500,
        'tools': 300,
        'marketing': 200,
        'insurance': 150
    })
    
    model.add_project(Project(
        project_id='PRJ-STARTUP-001',
        client='Local Business',
        total_value=8000,
        start_date=today - timedelta(days=10),
        estimated_end_date=today + timedelta(days=20),
        milestones=[
            {'name': 'Deliverable', 'amount': 8000, 
             'date': today + timedelta(days=20), 'paid': False}
        ],
        payments_received=0,
        work_completion_pct=15.0
    ))
    
    model.add_invoice(Invoice(
        invoice_id='INV-STARTUP-001',
        client='Local Business',
        amount=4000,
        issue_date=today - timedelta(days=5),
        due_date=today + timedelta(days=25),
        payment_terms_days=30,
        status=PaymentStatus.PENDING
    ))
    
    return model


def create_growth_model() -> CashFlowModel:
    """Model for a growing business (10+ employees)."""
    model = CashFlowModel(initial_balance=150000)
    
    today = datetime.now()
    
    model.set_monthly_fixed_costs({
        'salaries_full_time': 45000,
        'salaries_contractors': 12000,
        'office': 4500,
        'cloud_infrastructure': 3500,
        'software': 2800,
        'insurance': 3200,
        'marketing': 5000,
        'recruiting': 2000,
        'miscellaneous': 2000
    })
    
    projects_data = [
        ('Enterprise Client A', 150000, 60, 30, 45.0),
        ('Mid-Market Client B', 75000, 40, 50, 30.0),
        ('Startup Client C', 35000, 20, 40, 15.0),
        ('Retainer Client D', 12000, 0, 30, 100.0),
    ]
    
    for client, value, days_passed, days_remaining, work_pct in projects_data:
        model.add_project(Project(
            project_id=f'PRJ-GROWTH-{client[:3].upper()}',
            client=client,
            total_value=value,
            start_date=today - timedelta(days=days_passed),
            estimated_end_date=today + timedelta(days=days_remaining),
            milestones=[
                {'name': 'Milestone 1', 'amount': value * 0.4, 
                 'date': today + timedelta(days=10), 'paid': False},
                {'name': 'Milestone 2', 'amount': value * 0.6, 
                 'date': today + timedelta(days=days_remaining), 'paid': False}
            ],
            payments_received=0,
            work_completion_pct=work_pct
        ))
    
    model.add_invoice(Invoice(
        invoice_id='INV-GROWTH-001',
        client='Enterprise Client A',
        amount=60000,
        issue_date=today - timedelta(days=10),
        due_date=today + timedelta(days=20),
        payment_terms_days=30,
        status=PaymentStatus.PENDING
    ))
    
    model.add_invoice(Invoice(
        invoice_id='INV-GROWTH-002',
        client='Retainer Client D',
        amount=12000,
        issue_date=today - timedelta(days=5),
        due_date=today + timedelta(days=25),
        payment_terms_days=30,
        status=PaymentStatus.PENDING
    ))
    
    return model
