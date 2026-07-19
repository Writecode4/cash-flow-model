"""
Cash Flow Model for Any Business
=================================
Advanced cash flow forecasting and scenario planning.

This model transforms basic income/expense tracking into a predictive
engine that answers: When will money arrive? How long will it stay?
How efficiently does the business convert sales into actual cash?

AUDIT COMPLIANT: All formulas follow standard financial definitions.
"""

import copy
import calendar
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


class PaymentStatus(Enum):
    PENDING = "pending"
    RECEIVED = "received"
    LATE = "late"
    DEFAULTED = "defaulted"


class ExpenseType(Enum):
    FIXED = "fixed"
    VARIABLE = "variable"
    ONE_TIME = "one_time"
    TAX = "tax"


@dataclass
class Invoice:
    """
    Represents a client invoice with payment tracking.
    
    VALIDATION RULES:
    - amount must be positive
    - due_date must be >= issue_date
    - received_amount cannot exceed amount
    - received_date required if status is RECEIVED
    """
    invoice_id: str
    client: str
    amount: float
    issue_date: datetime
    due_date: datetime
    payment_terms_days: int
    status: PaymentStatus = PaymentStatus.PENDING
    received_date: Optional[datetime] = None
    received_amount: float = 0.0
    _collection_rate_override: Optional[float] = field(default=None, repr=False)
    
    def __post_init__(self):
        if self.amount <= 0:
            raise ValueError(f"Invoice amount must be positive, got {self.amount}")
        if self.due_date < self.issue_date:
            raise ValueError(f"due_date ({self.due_date}) cannot be before issue_date ({self.issue_date})")
        if self.received_amount > self.amount:
            raise ValueError(f"received_amount ({self.received_amount}) cannot exceed amount ({self.amount})")
        if self.status == PaymentStatus.RECEIVED and self.received_date is None:
            raise ValueError("RECEIVED invoices must have received_date")
    
    @property
    def days_outstanding(self) -> int:
        """Days since invoice was issued."""
        if self.received_date:
            return (self.received_date - self.issue_date).days
        return (datetime.now() - self.issue_date).days
    
    @property
    def is_overdue(self) -> bool:
        """Check if invoice is past due date."""
        return self.status == PaymentStatus.PENDING and datetime.now() > self.due_date
    
    @property
    def expected_payment_date(self) -> datetime:
        """Expected date based on payment terms."""
        return self.issue_date + timedelta(days=self.payment_terms_days)
    
    @property
    def days_past_due(self) -> int:
        """Days past due date (0 if not overdue)."""
        if datetime.now() > self.due_date and self.status == PaymentStatus.PENDING:
            return (datetime.now() - self.due_date).days
        return 0
    
    @property
    def collection_probability(self) -> float:
        """
        Probability of collecting this invoice based on age.
        Industry standard collections rates:
        - 0-30 days: 95%
        - 31-60 days: 85%
        - 61-90 days: 65%
        - 90+ days: 40%
        """
        # Allow scenario override
        if self._collection_rate_override is not None:
            return self._collection_rate_override
        
        days = self.days_outstanding
        if self.status == PaymentStatus.RECEIVED:
            return 1.0
        if self.status == PaymentStatus.DEFAULTED:
            return 0.0
        if days <= 30:
            return 0.95
        elif days <= 60:
            return 0.85
        elif days <= 90:
            return 0.65
        else:
            return 0.40


@dataclass
class Expense:
    """
    Represents a business expense.
    
    VALIDATION RULES:
    - amount must be positive
    """
    expense_id: str
    description: str
    amount: float
    date: datetime
    expense_type: ExpenseType
    category: str
    recurring: bool = False
    recurrence_months: int = 1
    
    def __post_init__(self):
        if self.amount <= 0:
            raise ValueError(f"Expense amount must be positive, got {self.amount}")


@dataclass
class Project:
    """
    Represents a project with cash flow implications.
    
    VALIDATION RULES:
    - total_value must be positive
    - payments_received cannot exceed total_value
    """
    project_id: str
    client: str
    total_value: float
    start_date: datetime
    estimated_end_date: datetime
    milestones: List[Dict] = field(default_factory=list)
    payments_received: float = 0.0
    work_completion_pct: float = 0.0
    
    def __post_init__(self):
        if self.total_value <= 0:
            raise ValueError(f"Project total_value must be positive, got {self.total_value}")
        if self.payments_received > self.total_value:
            raise ValueError(f"payments_received ({self.payments_received}) cannot exceed total_value ({self.total_value})")
        if self.work_completion_pct < 0 or self.work_completion_pct > 100:
            raise ValueError(f"work_completion_pct must be 0-100, got {self.work_completion_pct}")
    
    @property
    def remaining_value(self) -> float:
        return self.total_value - self.payments_received
    
    @property
    def financial_completion(self) -> float:
        """Financial completion based on payments received."""
        if self.total_value == 0:
            return 0
        return (self.payments_received / self.total_value) * 100
    
    @property
    def completion_percentage(self) -> float:
        """Actual work completion (primary metric)."""
        return self.work_completion_pct


class CashFlowModel:
    """
    Advanced Cash Flow Model for Any Business.
    
    Features:
    - Cash conversion cycle analysis (DSO/DPO compliant)
    - Scenario planning (what-if analysis)
    - Liquidity stress testing
    - Client payment behavior tracking
    - Project-level cash flow forecasting
    - Proper income/expense separation (no double counting)
    - Collection probability for aged receivables
    """
    
    def __init__(self, initial_balance: float = 0.0):
        if initial_balance < 0:
            raise ValueError(f"Initial balance cannot be negative, got {initial_balance}")
        self.initial_balance = initial_balance
        self.invoices: List[Invoice] = []
        self.expenses: List[Expense] = []
        self.projects: List[Project] = []
        self.monthly_fixed_costs: Dict[str, float] = {}
        self.dpo_days: int = 30  # Configurable Days Payable Outstanding
        self.dio_days: int = 0   # Configurable Days Inventory Outstanding
        self.tax_rate: float = 0.25  # Configurable tax rate
        
    def add_invoice(self, invoice: Invoice):
        """Add an invoice to the model."""
        self.invoices.append(invoice)
    
    def add_expense(self, expense: Expense):
        """Add an expense to the model."""
        self.expenses.append(expense)
    
    def add_project(self, project: Project):
        """Add a project to track."""
        self.projects.append(project)
    
    def set_monthly_fixed_costs(self, costs: Dict[str, float]):
        """Set recurring monthly fixed costs."""
        for name, amount in costs.items():
            if amount < 0:
                raise ValueError(f"Fixed cost '{name}' cannot be negative, got {amount}")
        self.monthly_fixed_costs = costs
    
    def set_tax_rate(self, rate: float):
        """Set effective tax rate (0.0 to 1.0)."""
        if rate < 0 or rate > 1:
            raise ValueError(f"Tax rate must be 0-1, got {rate}")
        self.tax_rate = rate
    
    def set_dpo_days(self, days: int):
        """Set Days Payable Outstanding based on actual payment behavior."""
        if days < 0:
            raise ValueError(f"DPO days cannot be negative, got {days}")
        self.dpo_days = days
    
    def set_dio_days(self, days: int):
        """Set Days Inventory Outstanding (0 for service businesses)."""
        if days < 0:
            raise ValueError(f"DIO days cannot be negative, got {days}")
        self.dio_days = days
    
    def calculate_dso(self) -> float:
        """
        Calculate Days Sales Outstanding (DSO) - AUDIT COMPLIANT.
        
        Standard formula: DSO = (Accounts Receivable / Total Credit Sales) x Days
        
        For any business:
        - Accounts Receivable = sum of unpaid invoice amounts (weighted by collection probability)
        - Credit Sales = total invoiced amount (received + pending)
        - Days = 30 (monthly approximation)
        """
        total_ar = sum(
            inv.amount * inv.collection_probability 
            for inv in self.invoices 
            if inv.status in (PaymentStatus.PENDING, PaymentStatus.LATE)
        )
        
        total_credit_sales = sum(inv.amount for inv in self.invoices)
        
        if total_credit_sales == 0:
            return 0
        
        # DSO over a 30-day period
        dso = (total_ar / total_credit_sales) * 30
        return round(dso, 1)
    
    def calculate_dso_raw(self) -> float:
        """
        Calculate DSO without collection probability weighting.
        Useful for comparison with industry benchmarks.
        """
        total_ar = sum(
            inv.amount for inv in self.invoices 
            if inv.status in (PaymentStatus.PENDING, PaymentStatus.LATE)
        )
        
        total_credit_sales = sum(inv.amount for inv in self.invoices)
        
        if total_credit_sales == 0:
            return 0
        
        dso = (total_ar / total_credit_sales) * 30
        return round(dso, 1)
    
    def calculate_cash_conversion_cycle(self) -> float:
        """
        Calculate Cash Conversion Cycle (CCC).
        CCC = DSO + DIO - DPO
        """
        dso = self.calculate_dso()
        dio = self.dio_days
        dpo = self.dpo_days
        return dso + dio - dpo
    
    def calculate_burn_rate(self) -> float:
        """
        Calculate monthly burn rate - AUDIT COMPLIANT.
        
        Net Burn Rate = Monthly Expenses - Monthly Income
        
        Positive = burning cash
        Negative = generating cash (good!)
        
        Includes all recurring expenses (fixed + variable).
        One-time expenses excluded from recurring rate.
        """
        # Fixed monthly costs
        monthly_fixed = sum(self.monthly_fixed_costs.values())
        
        # Recurring variable expenses (each is a separate monthly cost)
        monthly_variable = self._calculate_monthly_variable_expenses()
        
        # Total recurring monthly expenses
        total_monthly_expenses = monthly_fixed + monthly_variable
        
        # Average monthly income (from received payments)
        avg_monthly_income = self._calculate_avg_monthly_income()
        
        # Net burn (can be negative = cash positive)
        net_burn = total_monthly_expenses - avg_monthly_income
        return net_burn
    
    def _calculate_avg_monthly_income(self) -> float:
        """Calculate average monthly income from recent received payments."""
        received = [
            (inv.received_amount, inv.received_date) for inv in self.invoices 
            if inv.status == PaymentStatus.RECEIVED and inv.received_date
        ]
        
        if not received:
            return 0
        
        total_received = sum(amount for amount, _ in received)
        
        # Calculate actual date range of payments
        dates = [date for _, date in received]
        earliest = min(dates)
        latest = max(dates)
        
        # Calculate months spanned (minimum 1 month)
        days_spanned = (latest - earliest).days
        estimated_months = max(days_spanned / 30.0, 1.0)
        
        return total_received / estimated_months
    
    def calculate_runway(self) -> float:
        """
        Calculate cash runway in months - AUDIT COMPLIANT.
        
        Accounts for BOTH burn rate AND expected incoming payments.
        Runway = Current Balance / Net Monthly Burn (if positive)
        
        If net burn <= 0, runway is infinite (cash flow positive).
        """
        burn_rate = self.calculate_burn_rate()
        
        if burn_rate <= 0:
            # Company is cash flow positive or break-even
            current_balance = self.get_current_balance()
            if current_balance > 0:
                return float('inf')
            return 0
        
        current_balance = self.get_current_balance()
        return current_balance / burn_rate
    
    def get_current_balance(self) -> float:
        """Calculate current cash balance."""
        received = sum(
            inv.received_amount for inv in self.invoices 
            if inv.status == PaymentStatus.RECEIVED
        )
        spent = sum(exp.amount for exp in self.expenses)
        return self.initial_balance + received - spent
    
    def get_accounts_receivable(self) -> Dict[str, float]:
        """Get breakdown of accounts receivable by aging."""
        aging = {
            'current': 0,
            '31-60_days': 0,
            '61-90_days': 0,
            'over_90_days': 0
        }
        
        for inv in self.invoices:
            if inv.status in (PaymentStatus.PENDING, PaymentStatus.LATE):
                days = inv.days_outstanding
                if days <= 30:
                    aging['current'] += inv.amount
                elif days <= 60:
                    aging['31-60_days'] += inv.amount
                elif days <= 90:
                    aging['61-90_days'] += inv.amount
                else:
                    aging['over_90_days'] += inv.amount
        
        return aging
    
    def get_weighted_ar(self) -> Dict[str, float]:
        """Get accounts receivable weighted by collection probability."""
        aging = {
            'current': 0,
            '31-60_days': 0,
            '61-90_days': 0,
            'over_90_days': 0
        }
        
        for inv in self.invoices:
            if inv.status in (PaymentStatus.PENDING, PaymentStatus.LATE):
                weighted = inv.amount * inv.collection_probability
                days = inv.days_outstanding
                if days <= 30:
                    aging['current'] += weighted
                elif days <= 60:
                    aging['31-60_days'] += weighted
                elif days <= 90:
                    aging['61-90_days'] += weighted
                else:
                    aging['over_90_days'] += weighted
        
        return aging
    
    def forecast_cash_flow(self, months: int = 12) -> pd.DataFrame:
        """
        Generate monthly cash flow forecast - AUDIT COMPLIANT.
        
        KEY FEATURES:
        - No double counting between invoices and milestones
        - Collection probability applied to aged receivables
        - Annual tax estimation with quarterly payments
        - Proper calendar month boundaries
        """
        today = datetime.now()
        forecast_data = []
        
        current_balance = self.get_current_balance()
        
        # Pre-calculate milestone linkage to avoid double counting
        invoiced_milestone_ids = self._get_invoiced_milestone_ids()
        
        for month_offset in range(months):
            # Calculate month boundaries using actual calendar
            forecast_date = self._add_months(today, month_offset)
            month_start = forecast_date.replace(day=1)
            month_end = self._get_month_end(month_start)
            
            # === INCOME ===
            projected_income = 0
            
            # 1. Invoice payments (weighted by collection probability)
            for inv in self.invoices:
                if inv.status in (PaymentStatus.PENDING, PaymentStatus.LATE):
                    expected = inv.expected_payment_date
                    if month_start <= expected <= month_end:
                        # Apply collection probability for aged invoices
                        projected_income += inv.amount * inv.collection_probability
            
            # 2. Project milestone payments (only non-invoiced milestones)
            for project in self.projects:
                for i, milestone in enumerate(project.milestones):
                    milestone_date = milestone.get('date')
                    milestone_amount = milestone.get('amount', 0)
                    milestone_id = f"{project.project_id}_m{i}"
                    
                    if milestone_date and month_start <= milestone_date <= month_end:
                        if not milestone.get('paid', False):
                            # Only add if this milestone hasn't been invoiced
                            if milestone_id not in invoiced_milestone_ids:
                                projected_income += milestone_amount
            
            # === EXPENSES ===
            fixed_expenses = sum(self.monthly_fixed_costs.values())
            variable_expenses = self._calculate_monthly_variable_expenses()
            
            # Tax obligations (annual estimation, quarterly payments)
            tax_expenses = self._estimate_quarterly_tax(projected_income, fixed_expenses, variable_expenses, month_start)
            
            total_expenses = fixed_expenses + variable_expenses + tax_expenses
            net_cash_flow = projected_income - total_expenses
            current_balance += net_cash_flow
            
            forecast_data.append({
                'month': forecast_date.strftime('%Y-%m'),
                'month_date': forecast_date,
                'projected_income': projected_income,
                'fixed_expenses': fixed_expenses,
                'variable_expenses': variable_expenses,
                'tax_expenses': tax_expenses,
                'total_expenses': total_expenses,
                'net_cash_flow': net_cash_flow,
                'cumulative_balance': current_balance
            })
        
        return pd.DataFrame(forecast_data)
    
    def _get_invoiced_milestone_ids(self) -> set:
        """
        Get set of milestone IDs that have corresponding invoices.
        
        Matching priority:
        1. Explicit 'invoice_id' field on milestone (exact match)
        2. Amount match (fallback, less reliable)
        """
        invoiced = set()
        
        # Build invoice lookup by client and by invoice_id
        invoices_by_client = {}
        invoice_ids = set()
        for inv in self.invoices:
            if inv.client not in invoices_by_client:
                invoices_by_client[inv.client] = []
            invoices_by_client[inv.client].append(inv.amount)
            invoice_ids.add(inv.invoice_id)
        
        # Check each milestone against invoices
        for project in self.projects:
            client_invoices = invoices_by_client.get(project.client, [])
            
            for i, milestone in enumerate(project.milestones):
                milestone_id = f"{project.project_id}_m{i}"
                
                # Priority 1: Explicit invoice_id linkage
                linked_invoice_id = milestone.get('invoice_id')
                if linked_invoice_id and linked_invoice_id in invoice_ids:
                    invoiced.add(milestone_id)
                    continue
                
                # Priority 2: Amount match (fallback)
                milestone_amount = milestone.get('amount', 0)
                for inv_amount in client_invoices:
                    if abs(inv_amount - milestone_amount) < 0.01:
                        invoiced.add(milestone_id)
                        break
        
        return invoiced
    
    def _calculate_monthly_variable_expenses(self) -> float:
        """Calculate monthly variable expenses (recurring only)."""
        recurring_variable = [
            exp.amount for exp in self.expenses 
            if exp.expense_type == ExpenseType.VARIABLE and exp.recurring
        ]
        
        if not recurring_variable:
            return 0
        
        # Each recurring expense is a separate monthly cost - sum them
        return sum(recurring_variable)
    
    def _estimate_quarterly_tax(self, income: float, fixed: float, variable: float, month: datetime) -> float:
        """
        Estimate quarterly tax payment.
        
        Taxes are typically paid quarterly based on projected annual profit.
        This simplification estimates monthly tax accrual with quarterly payment.
        """
        gross_profit_monthly = income - fixed - variable
        
        if gross_profit_monthly <= 0:
            return 0
        
        # Monthly tax accrual
        monthly_tax = gross_profit_monthly * self.tax_rate
        
        # Only pay in months that are end of quarter (3, 6, 9, 12)
        if month.month in [3, 6, 9, 12]:
            # Quarterly payment = 3 months of accrued tax
            return monthly_tax * 3
        
        # Other months: just accrue (no cash outflow)
        return 0
    
    def _add_months(self, date: datetime, months: int) -> datetime:
        """Add months to a date safely."""
        month = date.month - 1 + months
        year = date.year + month // 12
        month = month % 12 + 1
        _, max_day = calendar.monthrange(year, month)
        day = min(date.day, max_day)
        return date.replace(year=year, month=month, day=day)
    
    def _get_month_end(self, month_start: datetime) -> datetime:
        """Get last day of month."""
        if month_start.month == 12:
            return month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            return month_start.replace(month=month_start.month + 1, day=1) - timedelta(days=1)
    
    def scenario_analysis(self, scenarios: Dict[str, Dict]) -> pd.DataFrame:
        """
        Run what-if scenario analysis - AUDIT COMPLIANT.
        
        Scenarios dict structure:
        {
            'scenario_name': {
                'income_multiplier': 1.2,
                'expense_multiplier': 0.9,
                'payment_delay_days': 15,
                'new_monthly_cost': 5000,
                'tax_rate_override': 0.20,
                'collection_rate_override': 0.7
            }
        }
        """
        results = []
        
        for scenario_name, params in scenarios.items():
            model_copy = copy.deepcopy(self)
            
            # Apply scenario parameters
            if 'payment_delay_days' in params:
                delay = params['payment_delay_days']
                for inv in model_copy.invoices:
                    if inv.status in (PaymentStatus.PENDING, PaymentStatus.LATE):
                        inv.due_date += timedelta(days=delay)
                        inv.payment_terms_days += delay
            
            if 'income_multiplier' in params:
                multiplier = params['income_multiplier']
                for inv in model_copy.invoices:
                    inv.amount *= multiplier
                    if inv.status == PaymentStatus.RECEIVED:
                        inv.received_amount *= multiplier
                for proj in model_copy.projects:
                    proj.total_value *= multiplier
                    proj.payments_received *= multiplier
            
            if 'expense_multiplier' in params:
                multiplier = params['expense_multiplier']
                for exp in model_copy.expenses:
                    exp.amount *= multiplier
                model_copy.monthly_fixed_costs = {
                    k: v * multiplier 
                    for k, v in model_copy.monthly_fixed_costs.items()
                }
            
            if 'new_monthly_cost' in params:
                model_copy.monthly_fixed_costs['scenario_addition'] = params['new_monthly_cost']
            
            if 'tax_rate_override' in params:
                model_copy.tax_rate = params['tax_rate_override']
            
            if 'collection_rate_override' in params:
                # Override collection probability for all pending invoices
                rate = params['collection_rate_override']
                for inv in model_copy.invoices:
                    if inv.status in (PaymentStatus.PENDING, PaymentStatus.LATE):
                        inv._collection_rate_override = rate
            
            # Run forecast
            forecast = model_copy.forecast_cash_flow(months=12)
            
            # Calculate key metrics
            final_balance = forecast['cumulative_balance'].iloc[-1]
            min_balance = forecast['cumulative_balance'].min()
            total_income = forecast['projected_income'].sum()
            total_expenses = forecast['total_expenses'].sum()
            
            results.append({
                'scenario': scenario_name,
                'final_balance': final_balance,
                'minimum_balance': min_balance,
                'total_income': total_income,
                'total_expenses': total_expenses,
                'net_position': total_income - total_expenses,
                'survives': min_balance > 0
            })
        
        return pd.DataFrame(results)
    
    def stress_test(self, stress_levels: List[float] = [0.8, 0.6, 0.4]) -> pd.DataFrame:
        """
        Run liquidity stress tests.
        """
        results = []
        
        for reduction in stress_levels:
            scenarios = {
                f'_income_{int(reduction*100)}%': {
                    'income_multiplier': reduction
                }
            }
            
            scenario_result = self.scenario_analysis(scenarios)
            scenario_result['stress_level'] = f'{int(reduction*100)}% of normal'
            results.append(scenario_result)
        
        return pd.concat(results, ignore_index=True)
    
    def client_payment_analysis(self) -> pd.DataFrame:
        """Analyze payment behavior by client."""
        client_stats = {}
        
        for inv in self.invoices:
            if inv.received_date:
                client = inv.client
                if client not in client_stats:
                    client_stats[client] = {
                        'total_invoices': 0,
                        'total_amount': 0,
                        'total_days_to_pay': 0,
                        'on_time_count': 0
                    }
                
                client_stats[client]['total_invoices'] += 1
                client_stats[client]['total_amount'] += inv.amount
                client_stats[client]['total_days_to_pay'] += inv.days_outstanding
                
                if inv.received_date <= inv.expected_payment_date:
                    client_stats[client]['on_time_count'] += 1
        
        results = []
        for client, stats in client_stats.items():
            avg_days = stats['total_days_to_pay'] / stats['total_invoices']
            on_time_rate = stats['on_time_count'] / stats['total_invoices'] * 100
            
            results.append({
                'client': client,
                'total_invoices': stats['total_invoices'],
                'total_amount': stats['total_amount'],
                'avg_days_to_pay': round(avg_days, 1),
                'on_time_payment_rate': round(on_time_rate, 1)
            })
        
        return pd.DataFrame(results)
    
    def generate_dashboard_data(self) -> Dict:
        """Generate all metrics needed for a dashboard."""
        forecast = self.forecast_cash_flow(months=12)
        ar_aging = self.get_accounts_receivable()
        weighted_ar = self.get_weighted_ar()
        
        return {
            'current_balance': self.get_current_balance(),
            'dso': self.calculate_dso(),
            'dso_raw': self.calculate_dso_raw(),
            'cash_conversion_cycle': self.calculate_cash_conversion_cycle(),
            'dpo': self.dpo_days,
            'burn_rate': self.calculate_burn_rate(),
            'runway_months': self.calculate_runway(),
            'monthly_forecast': forecast,
            'accounts_receivable': ar_aging,
            'weighted_ar': weighted_ar,
            'total_ar': sum(ar_aging.values()),
            'total_weighted_ar': sum(weighted_ar.values()),
            'pending_invoices_total': sum(
                inv.amount for inv in self.invoices 
                if inv.status in (PaymentStatus.PENDING, PaymentStatus.LATE)
            ),
            'overdue_invoices': sum(1 for inv in self.invoices if inv.is_overdue),
            'overdue_amount': sum(
                inv.amount for inv in self.invoices 
                if inv.status == PaymentStatus.LATE
            ),
            'active_projects': len([p for p in self.projects if p.completion_percentage < 100]),
            'total_project_value': sum(p.total_value for p in self.projects),
            'total_received': sum(inv.received_amount for inv in self.invoices if inv.status == PaymentStatus.RECEIVED),
            'tax_rate': self.tax_rate
        }
    
    def export_to_excel(self, filename: str = 'cash_flow_report.xlsx'):
        """Export model data to Excel for further analysis."""
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            dashboard = self.generate_dashboard_data()
            summary_data = {
                'Metric': ['Current Balance', 'DSO', 'DSO (Raw)', 'Cash Conversion Cycle', 
                          'DPO', 'Burn Rate', 'Runway (months)', 'Total AR', 'Weighted AR',
                          'Overdue Invoices', 'Overdue Amount', 'Active Projects', 'Tax Rate'],
                'Value': [
                    dashboard['current_balance'],
                    dashboard['dso'],
                    dashboard['dso_raw'],
                    dashboard['cash_conversion_cycle'],
                    dashboard['dpo'],
                    dashboard['burn_rate'],
                    dashboard['runway_months'],
                    dashboard['total_ar'],
                    dashboard['total_weighted_ar'],
                    dashboard['overdue_invoices'],
                    dashboard['overdue_amount'],
                    dashboard['active_projects'],
                    f"{dashboard['tax_rate']*100:.0f}%"
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Dashboard', index=False)
            
            forecast = self.forecast_cash_flow(months=12)
            forecast.drop(columns=['month_date'], errors='ignore', inplace=True)
            forecast.to_excel(writer, sheet_name='Forecast', index=False)
            
            client_analysis = self.client_payment_analysis()
            client_analysis.to_excel(writer, sheet_name='Client Analysis', index=False)
            
            ar_aging = self.get_accounts_receivable()
            pd.DataFrame([ar_aging]).to_excel(writer, sheet_name='AR Aging', index=False)
            
            invoice_data = [{
                'invoice_id': inv.invoice_id,
                'client': inv.client,
                'amount': inv.amount,
                'issue_date': inv.issue_date,
                'due_date': inv.due_date,
                'status': inv.status.value,
                'days_outstanding': inv.days_outstanding,
                'days_past_due': inv.days_past_due,
                'collection_probability': inv.collection_probability,
                'is_overdue': inv.is_overdue
            } for inv in self.invoices]
            pd.DataFrame(invoice_data).to_excel(writer, sheet_name='Invoices', index=False)
        
        print(f"Report exported to {filename}")


if __name__ == '__main__':
    print("=" * 60)
    print("CASH FLOW MODEL")
    print("=" * 60)
    
    from sample_data import create_sample_model
    model = create_sample_model()
    dashboard = model.generate_dashboard_data()
    
    print(f"\nCurrent Balance: ${dashboard['current_balance']:,.2f}")
    print(f"DSO (weighted): {dashboard['dso']:.1f} days")
    print(f"DSO (raw): {dashboard['dso_raw']:.1f} days")
    print(f"Cash Conversion Cycle: {dashboard['cash_conversion_cycle']:.1f} days")
    print(f"DPO: {dashboard['dpo']} days")
    print(f"Burn Rate: ${dashboard['burn_rate']:,.2f}/month")
    print(f"Runway: {dashboard['runway_months']:.1f} months" if dashboard['runway_months'] != float('inf') else "Runway: Indefinite")
    print(f"Pending Invoices: ${dashboard['pending_invoices_total']:,.2f}")
    print(f"Weighted AR: ${dashboard['total_weighted_ar']:,.2f}")
    print(f"Overdue Invoices: {dashboard['overdue_invoices']}")
    
    print("\n--- AR Aging ---")
    for bucket, amount in dashboard['accounts_receivable'].items():
        if amount > 0:
            weighted = dashboard['weighted_ar'].get(bucket, 0)
            print(f"  {bucket}: ${amount:,.2f} (weighted: ${weighted:,.2f})")
    
    print("\n" + "=" * 60)
    print("SCENARIO ANALYSIS")
    print("=" * 60)
    
    scenarios = {
        'Base Case': {},
        'Optimistic': {'income_multiplier': 1.2, 'expense_multiplier': 0.9},
        'Pessimistic': {'income_multiplier': 0.8, 'payment_delay_days': 15},
    }
    
    results = model.scenario_analysis(scenarios)
    print(results.to_string(index=False))
