"""
API connectors - import real data into the Cash Flow Model.

- StripeConnector: invoices, payments and expenses from the Stripe API.
- QuickBooksConnector: invoices, payments and bills from QuickBooks Online.

Connectors are designed to be testable offline: pass plain dicts (the native
API payload shapes) to `to_model()`; call `fetch()` only when you have live
credentials and the relevant SDK/package installed.
"""

from connectors.stripe import StripeConnector
from connectors.quickbooks import QuickBooksConnector

__all__ = ['StripeConnector', 'QuickBooksConnector']
