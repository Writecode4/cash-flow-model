"""
QuickBooks Online connector - import invoices, payments and bills.

QBO native payload shapes are accepted by `to_model()` for offline testing.
Live API access requires an OAuth2 access token, realm ID and the `requests`
package (QuickBooks' data service is a simple HTTP JSON API, no SDK needed).

QuickBooks amounts are already in major units and dates are ISO strings.
"""

import copy
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from cash_flow_model import (
    CashFlowModel, Invoice, Expense, PaymentStatus, ExpenseType
)

from connectors.base import ConnectorError


class QuickBooksConnector:
    """
    Maps QuickBooks Online records (Invoice, Payment, Bill) into a validated
    CashFlowModel.

    Status derivation for an invoice without an explicit status:
        Balance <= 0                     -> RECEIVED
        Balance > 0 and DueDate < today  -> LATE
        otherwise                        -> PENDING
    """

    QB_API_BASE = 'https://api.quickbooks.com/v3/company/{realm_id}'

    def __init__(self, access_token: Optional[str] = None, realm_id: Optional[str] = None):
        self.access_token = access_token
        self.realm_id = realm_id

    # === LIVE API ===

    def fetch(self, limit: int = 100) -> Dict:
        """Fetch recent invoices, payments and bills from QuickBooks Online."""
        try:
            import requests
        except ImportError:
            raise ConnectorError(
                "The 'requests' package is required for live QuickBooks access. "
                "Install it with: pip install requests"
            )
        if not self.access_token or not self.realm_id:
            raise ConnectorError(
                "QuickBooks access_token and realm_id are required for fetch()."
            )

        headers = {'Authorization': f'Bearer {self.access_token}'}
        base = self.QB_API_BASE.format(realm_id=self.realm_id)

        def query(entity: str) -> List[Dict]:
            url = f"{base}/query"
            params = {
                'query': f"select * from {entity} orderby TxnDate desc maxresults {limit}"
            }
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            body = resp.json()
            key = {'Invoice': 'Invoice', 'Payment': 'Payment', 'Bill': 'Bill'}[entity]
            return body.get('QueryResponse', {}).get(key, [])

        return {
            'invoices': query('Invoice'),
            'payments': query('Payment'),
            'expenses': query('Bill'),
        }

    # === PARSING (offline-testable) ===

    @staticmethod
    def _parse_date(value) -> Optional[datetime]:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))

    @classmethod
    def _map_status(cls, status: str) -> Optional[PaymentStatus]:
        status = (status or '').lower()
        if status in ('paid', 'received'):
            return PaymentStatus.RECEIVED
        if status in ('late', 'past_due', 'overdue'):
            return PaymentStatus.LATE
        if status in ('defaulted', 'uncollectible'):
            return PaymentStatus.DEFAULTED
        if status in ('pending', 'open'):
            return PaymentStatus.PENDING
        # 'void' / 'deleted' -> no cash impact
        return None

    @classmethod
    def parse_invoice(cls, record: Dict, payments: Optional[List[Dict]] = None) -> Optional[Invoice]:
        """
        Build an Invoice from a QuickBooks Invoice record.

        Returns None for invoices with no cash impact (void/deleted).
        """
        payments = payments or []
        inv_id = str(record.get('Id') or '')
        if not inv_id:
            raise ConnectorError("QuickBooks invoice record is missing 'Id'.")

        amount = float(record.get('TotalAmt') or 0)
        balance = float(record.get('Balance')) if record.get('Balance') is not None else amount
        if amount <= 0:
            # No cash impact (e.g. $0 invoices)
            return None

        customer_ref = record.get('CustomerRef') or {}
        client = (
            customer_ref.get('name') if isinstance(customer_ref, dict) else str(customer_ref)
        ) or record.get('CustomerMemo') or 'Unknown'

        txn_date = cls._parse_date(record.get('TxnDate'))
        due_date = cls._parse_date(record.get('DueDate'))
        if txn_date and due_date:
            terms = max((due_date - txn_date).days, 1)
        else:
            terms = 30
        if due_date is None:
            due_date = (txn_date or datetime.now()) + timedelta(days=terms)

        status_enum = cls._map_status(record.get('status'))
        if status_enum is None and 'status' in record:
            return None  # explicit void/deleted
        if status_enum is None:
            if balance <= 0:
                status_enum = PaymentStatus.RECEIVED
            elif due_date < datetime.now():
                status_enum = PaymentStatus.LATE
            else:
                status_enum = PaymentStatus.PENDING

        received_date = None
        received_amount = 0.0

        if status_enum == PaymentStatus.RECEIVED:
            received_amount = max(amount - balance, 0.0)
            for p in payments:
                refs = p.get('LinkedTxn') or []
                for ref in refs:
                    if ref and str(ref.get('TxnId')) == inv_id:
                        received_date = cls._parse_date(p.get('TxnDate')) or received_date
                        if p.get('TotalAmt'):
                            received_amount = float(p['TotalAmt'])
                        break
            received_date = received_date or due_date

        return Invoice(
            invoice_id=inv_id,
            client=client,
            amount=amount,
            issue_date=txn_date or datetime.now() - timedelta(days=terms),
            due_date=due_date,
            payment_terms_days=terms,
            status=status_enum,
            received_date=received_date,
            received_amount=received_amount,
        )

    @classmethod
    def parse_expense(cls, record: Dict) -> Optional[Expense]:
        """Build an Expense from a QuickBooks Bill record."""
        exp_id = str(record.get('Id') or '')
        if not exp_id:
            raise ConnectorError("QuickBooks bill record is missing 'Id'.")
        amount = float(record.get('TotalAmt') or 0)
        date = cls._parse_date(record.get('TxnDate')) or datetime.now()
        vendor_ref = record.get('VendorRef') or {}
        description = (
            vendor_ref.get('name') if isinstance(vendor_ref, dict) else str(vendor_ref)
        ) or 'Expense'
        return Expense(
            expense_id=exp_id,
            description=description,
            amount=amount,
            date=date,
            expense_type=ExpenseType(record.get('expense_type', 'variable')),
            category=record.get('category', 'General'),
            recurring=bool(record.get('recurring', False)),
        )

    # === MODEL BUILDING ===

    def to_model(self, data: Dict, config: Optional[Dict] = None) -> CashFlowModel:
        """
        Build a CashFlowModel from a QuickBooks-shaped payload.

        Expected shape:
            {
                'invoices': [...],   # QBO Invoice objects
                'payments': [...],   # QBO Payment objects
                'expenses': [...],   # QBO Bill objects
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
