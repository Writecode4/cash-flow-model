"""
Connector base class.

Provides the shared contract for API connectors. Subclasses implement:
- fetch(): hit the live API and return a plain-dict payload.
- to_model(data, config=None): build a validated CashFlowModel from a payload.
"""

from typing import Dict, Optional


class ConnectorError(Exception):
    """Raised when a connector cannot fetch or parse data."""


class BaseConnector:
    """Contract every data connector must satisfy."""

    def fetch(self, **kwargs) -> Dict:
        """Fetch raw records from the external API and return plain dicts."""
        raise NotImplementedError

    def to_model(self, data: Dict, config: Optional[Dict] = None):
        """Build a CashFlowModel from a raw payload. Imported lazily to keep
        connectors usable without heavyweight model imports."""
        raise NotImplementedError
