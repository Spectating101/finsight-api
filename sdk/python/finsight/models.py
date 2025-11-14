"""
Data models for FinSight SDK
"""

from dataclasses import dataclass
from typing import Optional, List, Dict
from datetime import datetime


@dataclass
class Metric:
    """Financial metric with value and citation"""

    name: str
    value: float
    unit: str
    date: str
    citation: Optional['Citation'] = None

    @classmethod
    def from_dict(cls, data: Dict) -> 'Metric':
        """Create Metric from API response"""
        citation = Citation.from_dict(data['citation']) if 'citation' in data else None

        return cls(
            name=data['name'],
            value=data['value'],
            unit=data.get('unit', 'USD'),
            date=data['date'],
            citation=citation
        )

    def __str__(self) -> str:
        return f"{self.name}: {self.value:,.2f} {self.unit} ({self.date})"


@dataclass
class Citation:
    """Citation for data source"""

    source: str
    form: str
    filing_date: str
    url: str

    @classmethod
    def from_dict(cls, data: Dict) -> 'Citation':
        """Create Citation from API response"""
        return cls(
            source=data.get('source', 'SEC EDGAR'),
            form=data.get('form', ''),
            filing_date=data.get('filing_date', ''),
            url=data.get('url', '')
        )

    def __str__(self) -> str:
        return f"Source: {self.source} {self.form} ({self.filing_date})"


@dataclass
class Company:
    """Company information"""

    ticker: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    cik: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict) -> 'Company':
        """Create Company from API response"""
        return cls(
            ticker=data['ticker'],
            name=data['name'],
            sector=data.get('sector'),
            industry=data.get('industry'),
            description=data.get('description'),
            website=data.get('website'),
            cik=data.get('cik')
        )

    def __str__(self) -> str:
        return f"{self.ticker}: {self.name}"


@dataclass
class Subscription:
    """User subscription details"""

    tier: str
    status: str
    usage: int
    limit: int
    requests_remaining: int
    reset_date: str

    @classmethod
    def from_dict(cls, data: Dict) -> 'Subscription':
        """Create Subscription from API response"""
        return cls(
            tier=data['tier'],
            status=data.get('status', 'active'),
            usage=data['usage'],
            limit=data['limit'],
            requests_remaining=data.get('requests_remaining', 0),
            reset_date=data.get('reset_date', '')
        )

    def __str__(self) -> str:
        return f"{self.tier.upper()} tier - {self.usage}/{self.limit} requests used"

    @property
    def usage_percentage(self) -> float:
        """Calculate usage as percentage"""
        if self.limit == 0:
            return 0.0
        return (self.usage / self.limit) * 100

    @property
    def is_near_limit(self) -> bool:
        """Check if usage is near limit (>80%)"""
        return self.usage_percentage > 80


@dataclass
class APIKey:
    """API key metadata"""

    key_id: int
    name: Optional[str]
    prefix: str
    created_at: str
    last_used: Optional[str] = None
    expires_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict) -> 'APIKey':
        """Create APIKey from API response"""
        return cls(
            key_id=data['key_id'],
            name=data.get('name'),
            prefix=data['prefix'],
            created_at=data['created_at'],
            last_used=data.get('last_used'),
            expires_at=data.get('expires_at')
        )

    def __str__(self) -> str:
        name = self.name or "Unnamed key"
        return f"{name} ({self.prefix}...)"


@dataclass
class PricingTier:
    """Pricing tier information"""

    name: str
    price_monthly: float
    requests_per_minute: int
    requests_per_month: int
    features: List[str]

    @classmethod
    def from_dict(cls, data: Dict) -> 'PricingTier':
        """Create PricingTier from API response"""
        return cls(
            name=data['name'],
            price_monthly=data['price_monthly'],
            requests_per_minute=data['requests_per_minute'],
            requests_per_month=data['requests_per_month'],
            features=data.get('features', [])
        )

    def __str__(self) -> str:
        return f"{self.name.upper()}: ${self.price_monthly}/month"
