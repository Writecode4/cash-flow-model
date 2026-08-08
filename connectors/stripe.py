"""
Stripe connector - import invoices, payments and expenses from Stripe.

Stripe native payload shapes are accepted by `to_model()` so the connector is
fully testable offline. Live API access requires the `stripe` SDK and an API key.

Stripe amounts are minor units (cents) - this connector converts them to major
units (currency) automatically.
"""

import copy
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from cash_flow_model import (
    CashFlowModel, Invoice, Expense, PaymentStatus, ExpenseType
)

from connectors.base import ConnectorError


class StripeConnector:
    """
    Maps Stripe API records (invoices, charges/payments, expenses) into a
    validated CashFlowModel.

    Status mapping (Stripe invoice status -> PaymentStatus):
        paid                       -> RECEIVED
        open                       -> PENDING
        past_due                   -> LATE
        uncollectible              -> DEFAULTED
        draft / void               -> skipped (no cash impact)
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    # === LIVE API ===

    def fetch(self, limit: int = 100) -> Dict:
        """Fetch recent invoices and charges from the Stripe API."""
        try:
            import stripe
        except ImportError:
            raise ConnectorError(
                "The 'stripe' package is required for live API access. "
                "Install it with: pip install stripe"
            )
        if not self.api_key:
            raise ConnectorError("Stripe API key is required for fetch().")

        stripe.api_key = self.api_key
        invoices = list(stripe.Invoice.list(limit=limit).auto_paging_iter())
        payments = list(stripe.Charge.list(limit=limit).auto_paging_iter())
        return {
            'invoices': [i.to_dict_recursive() for i in invoices],
            'payments': [c.to_dict_recursive() for c in payments],
            'expenses': [],
        }

    # === PARSING (offline-testable) ===

    @staticmethod
    def _to_major(value) -> float:
        """Convert Stripe minor units (cents) to major units (currency)."""
        return float(value or 0) / 100.0

    @staticmethod
    def _unix_to_datetime(ts, default: Optional[datetime] = None) -> Optional[datetime]:
        if not ts:
            return default
        return datetime.fromtimestamp(float(ts))

    @classmethod
    def _map_status(cls, status: str) -> Optional[PaymentStatus]:
        status = (status or '').lower()
        if status in ('paid', 'succeeded'):
            return PaymentStatus.RECEIVED
        if status in ('past_due', 'overdue'):
            return PaymentStatus.LATE
        if status in ('uncollectible', 'defaulted'):
            return PaymentStatus.DEFAULTED
        if status in ('open', 'pending'):
            return PaymentStatus.PENDING
        # draft / void -> not cash-relevant
        return None

    @classmethod
    def parse_invoice(cls, record: Dict, payments: Optional[List[Dict]] = None) -> Optional[Invoice]:
        """
        Build an Invoice from a Stripe invoice record.

        Returns None for invoices with no cash impact (draft/void).
        """
        payments = payments or []
        status_enum = cls._map_status(record.get('status', 'open'))
        if status_enum is None:
            return None

        inv_id = str(record.get('id') or record.get('invoice_id') or '')
        if not inv_id:
            raise ConnectorError("Stripe invoice record is missing 'id'.")

        amount = cls._to_major(record.get('total') or record.get('amount_due') or 0)
        if amount <= 0:
            # No cash impact (e.g. $0 or fully discounted invoices)
            return None
        client = (
            record.get('customer_name')
            or record.get('customer_email')
            or record.get('customer')
            or 'Unknown'
        )

        created = cls._unix_to_datetime(record.get('created'))
        due = cls._unix_to_datetime(record.get('due_date'))
        if created and due:
            terms = max((due - created).days, 1)
        else:
            terms = 30
        if due is None:
            due = (created or datetime.now()) + timedelta(days=terms)

        received_date = None
        received_amount = 0.0

        if status_enum == PaymentStatus.RECEIVED:
            received_amount = amount
            for p in payments:
                ref = p.get('invoice')
                ref_id = ref.get('id') if isinstance(ref, dict) else ref
                if ref_id and str(ref_id) == inv_id:
                    paid_at = cls._unix_to_datetime(p.get('created'))
                    received_date = paid_at or due
                    received_amount = cls._to_major(
                        p.get('amount_captured') or p.get('amount') or amount
                    )
                    break
            received_date = received_date or due

        return Invoice(
            invoice_id=inv_id,
            client=client,
            amount=amount,
            issue_date=created or datetime.now() - timedelta(days=terms),
            due_date=due,
            payment_terms_days=terms,
            status=status_enum,
            received_date=received_date,
            received_amount=received_amount,
        )

    @classmethod
    def parse_expense(cls, record: Dict) -> Optional[Expense]:
        """Build an Expense from a generic record (amount in minor units)."""
        exp_id = str(record.get('id') or record.get('expense_id') or '')
        if not exp_id:
            raise ConnectorError("Stripe expense record is missing 'id'.")
        amount = cls._to_major(record.get('amount') or 0)
        date = cls._unix_to_datetime(record.get('created')) or datetime.now()
        exp_type = ExpenseType(record.get('expense_type', 'variable'))
        return Expense(
            expense_id=exp_id,
            description=record.get('description', 'Expense'),
            amount=amount,
            date=date,
            expense_type=exp_type,
            category=record.get('category', 'General'),
            recurring=bool(record.get('recurring', False)),
        )

    # === MODEL BUILDING ===

    def to_model(self, data: Dict, config: Optional[Dict] = None) -> CashFlowModel:
        """
        Build a CashFlowModel from a Stripe-shaped payload.

        Expected shape (Stripe native keys):
            {
                'invoices': [...],   # Stripe invoice objects
                'payments': [...],   # Stripe charge objects
                'expenses': [...],   # optional, generic records
            }
        """
        config = config or {}
        model = CashFlowModel(initial_balance=config.get('initial_balance', 0))
        model.set_dpo_days(config.get('dpo_days', 30))
        model.set_dio_days(config.get('dio_days', 0))
        model.set_tax_rate(config.get('tax_rate', 0.25))
        model.set_sales_tax_rate(config.get('sales_tax_rate', 0.0))
        if config.get('monthly_fixed_costs'):
            model.set_monthly_fixed_costs(config['monthly_fixed_costs'])

        payments = data.get('payments', [])
        for rec in data.get('invoices', []):
            inv = self.parse_invoice(rec, payments=payments)
            if inv is not None:
                model.add_invoice(inv)

        for rec in data.get('expenses', []):
            exp = self.parse_expense(rec)
            if exp is not None:
                model.add_expense(exp)

        return model
