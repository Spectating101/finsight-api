"""
Base DataSource Plugin Interface
Extensible architecture for adding new financial data sources
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel


class DataSourceType(str, Enum):
    """Types of data sources"""
    SEC_EDGAR = "sec_edgar"
    YAHOO_FINANCE = "yahoo_finance"
    ALPHA_VANTAGE = "alpha_vantage"
    POLYGON_IO = "polygon_io"
    FINANCIAL_MODELING_PREP = "financial_modeling_prep"
    INTRINIO = "intrinio"
    BLOOMBERG = "bloomberg"  # Future
    CUSTOM = "custom"


class DataSourceCapability(str, Enum):
    """Capabilities a data source can provide"""
    FUNDAMENTALS = "fundamentals"  # Balance sheet, income statement
    MARKET_DATA = "market_data"  # Prices, volume
    REAL_TIME = "real_time"  # Live prices
    HISTORICAL = "historical"  # Historical data
    FILINGS = "filings"  # SEC filings, documents
    NEWS = "news"  # News articles
    INSIDER_TRADING = "insider_trading"
    OWNERSHIP = "ownership"  # Institutional ownership
    EARNINGS = "earnings"  # Earnings calls, transcripts


class FinancialData(BaseModel):
    """Standardized financial data response"""
    source: DataSourceType
    ticker: str
    concept: str  # e.g., "revenue", "netIncome", "totalAssets"
    value: float
    unit: str  # "USD", "shares", "percent"
    period: str  # "2023-Q4", "2023", "ttm"
    period_type: str  # "duration", "instant"

    # Citation
    citation: Dict[str, Any]  # Source-specific citation data

    # Metadata
    retrieved_at: datetime
    confidence: Optional[float] = None  # Data quality score 0-1


class DataSourcePlugin(ABC):
    """
    Abstract base class for data source plugins

    All data sources must implement this interface to be compatible
    with FinSight's calculation engine and API routing
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize data source with configuration

        Args:
            config: Configuration dict (API keys, endpoints, etc.)
        """
        self.config = config
        self.source_type = self.get_source_type()
        self.capabilities = self.get_capabilities()

    @abstractmethod
    def get_source_type(self) -> DataSourceType:
        """Return the data source type identifier"""
        pass

    @abstractmethod
    def get_capabilities(self) -> List[DataSourceCapability]:
        """Return list of capabilities this source provides"""
        pass

    @abstractmethod
    async def get_financial_data(
        self,
        ticker: str,
        concepts: List[str],
        period: Optional[str] = None
    ) -> List[FinancialData]:
        """
        Fetch financial data for given ticker and concepts

        Args:
            ticker: Company ticker symbol
            concepts: List of financial concepts (e.g., ["revenue", "netIncome"])
            period: Optional period filter (e.g., "2023-Q4", "ttm")

        Returns:
            List of FinancialData objects
        """
        pass

    @abstractmethod
    async def search_companies(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for companies by name, ticker, or CIK

        Args:
            query: Search query

        Returns:
            List of company info dicts
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if data source is available and credentials are valid

        Returns:
            True if healthy, False otherwise
        """
        pass

    def supports_capability(self, capability: DataSourceCapability) -> bool:
        """Check if this source supports a given capability"""
        return capability in self.capabilities

    def get_rate_limit(self) -> Optional[int]:
        """
        Return rate limit for this source (requests per minute)
        Override in subclass if rate limited
        """
        return None

    def get_cost_per_call(self) -> Optional[float]:
        """
        Return cost per API call (for cost tracking)
        Override in subclass if applicable
        """
        return None


class DataSourceRegistry:
    """
    Registry for data source plugins
    Allows dynamic registration and lookup of data sources
    """

    def __init__(self):
        self._sources: Dict[DataSourceType, DataSourcePlugin] = {}

    def register(self, source: DataSourcePlugin):
        """Register a data source plugin"""
        self._sources[source.source_type] = source

    def get(self, source_type: DataSourceType) -> Optional[DataSourcePlugin]:
        """Get a registered data source by type"""
        return self._sources.get(source_type)

    def get_by_capability(self, capability: DataSourceCapability) -> List[DataSourcePlugin]:
        """Get all sources that support a given capability"""
        return [
            source for source in self._sources.values()
            if source.supports_capability(capability)
        ]

    def list_all(self) -> List[DataSourcePlugin]:
        """List all registered data sources"""
        return list(self._sources.values())

    async def health_check_all(self) -> Dict[DataSourceType, bool]:
        """Run health checks on all registered sources"""
        results = {}
        for source_type, source in self._sources.items():
            try:
                results[source_type] = await source.health_check()
            except Exception:
                results[source_type] = False
        return results


# Global registry instance
_registry = DataSourceRegistry()


def get_registry() -> DataSourceRegistry:
    """Get the global data source registry"""
    return _registry


def register_source(source: DataSourcePlugin):
    """Convenience function to register a data source"""
    _registry.register(source)
