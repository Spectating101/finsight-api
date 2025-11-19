"""
RAG Cache Layer - Redis-backed static context caching
"""

import json
import structlog
from typing import Optional, Dict
from redis.asyncio import Redis

logger = structlog.get_logger(__name__)


# Pre-built company contexts (static, cache for 24 hours)
RAG_CONTEXT_CACHE = {
    "AAPL": {
        "company_name": "Apple Inc.",
        "sector": "Technology",
        "description": "Apple Inc. is a technology leader with strong brand loyalty, premium pricing power, and a diversified ecosystem (iPhone, Mac, Services, Wearables). Known for high margins and massive cash reserves.",
        "key_strengths": ["Brand loyalty", "Ecosystem lock-in", "High margins", "Cash reserves"],
        "key_risks": ["iPhone dependency", "China exposure", "Regulatory pressure", "Market saturation"]
    },
    "MSFT": {
        "company_name": "Microsoft Corporation",
        "sector": "Technology",
        "description": "Microsoft dominates enterprise cloud computing with Azure, while maintaining strong positions in productivity software (Office 365) and gaming (Xbox). Consistent revenue growth from cloud transition.",
        "key_strengths": ["Azure growth", "Enterprise relationships", "Recurring revenue", "AI leadership"],
        "key_risks": ["Cloud competition", "Enterprise spending cycles", "Regulatory scrutiny"]
    },
    "GOOGL": {
        "company_name": "Alphabet Inc.",
        "sector": "Technology",
        "description": "Alphabet (Google) dominates digital advertising with search and YouTube. Strong positions in cloud computing (GCP), mobile OS (Android), and emerging AI technologies.",
        "key_strengths": ["Search dominance", "Ad platform scale", "AI/ML capabilities", "YouTube"],
        "key_risks": ["Regulatory antitrust", "Ad market cycles", "Competition from TikTok/Meta"]
    },
    "AMZN": {
        "company_name": "Amazon.com Inc.",
        "sector": "Consumer Cyclical",
        "description": "Amazon leads e-commerce and cloud infrastructure (AWS). AWS provides majority of operating income despite being smaller revenue segment. Expanding into advertising and healthcare.",
        "key_strengths": ["AWS profitability", "E-commerce scale", "Logistics network", "Prime ecosystem"],
        "key_risks": ["E-commerce margin pressure", "Labor costs", "AWS competition", "Regulatory pressure"]
    },
    "NVDA": {
        "company_name": "NVIDIA Corporation",
        "sector": "Technology",
        "description": "NVIDIA dominates AI/ML accelerator chips (GPUs) with CUDA ecosystem advantage. Benefiting massively from generative AI boom. High growth but cyclical semiconductor exposure.",
        "key_strengths": ["AI chip dominance", "CUDA moat", "Pricing power", "Data center growth"],
        "key_risks": ["Competition from AMD/Intel/custom chips", "Cyclical semiconductor market", "High valuation", "China restrictions"]
    },
    "TSLA": {
        "company_name": "Tesla Inc.",
        "sector": "Consumer Cyclical",
        "description": "Tesla leads electric vehicle manufacturing with vertically integrated approach and charging network advantage. Expanding into energy storage and autonomous driving technology.",
        "key_strengths": ["EV market leadership", "Charging network", "Battery technology", "Brand strength"],
        "key_risks": ["Competition intensifying", "Production challenges", "Valuation concerns", "Key person risk"]
    },
    "JPM": {
        "company_name": "JPMorgan Chase & Co.",
        "sector": "Financial Services",
        "description": "JPMorgan Chase is the largest U.S. bank by assets, with diversified operations across consumer banking, investment banking, and asset management. Strong balance sheet and consistent performance through cycles.",
        "key_strengths": ["Diversified business model", "Strong risk management", "Scale advantages", "Digital banking"],
        "key_risks": ["Interest rate sensitivity", "Regulatory costs", "Credit cycle exposure", "Economic downturn"]
    },
    "GS": {
        "company_name": "Goldman Sachs Group Inc.",
        "sector": "Financial Services",
        "description": "Goldman Sachs is a leading investment banking and securities firm. Strong in trading, M&A advisory, and asset management. More cyclical than diversified banks due to capital markets focus.",
        "key_strengths": ["Investment banking leadership", "Trading expertise", "Wealthy client relationships"],
        "key_risks": ["Market volatility", "Deal flow cycles", "Trading losses", "Competitive pressure"]
    }
}


class RAGCache:
    """Redis-backed cache for static company contexts"""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.ttl = 86400  # 24 hour cache for company info

    async def get_company_context(self, ticker: str) -> Optional[Dict]:
        """
        Retrieve cached company context.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dict with company context or None if not found
        """
        # First check pre-built cache
        if ticker in RAG_CONTEXT_CACHE:
            logger.info("RAG cache hit (pre-built)", ticker=ticker)
            return RAG_CONTEXT_CACHE[ticker]

        # Then check Redis
        key = f"company_context:{ticker}"
        try:
            data = await self.redis.get(key)
            if data:
                logger.info("RAG cache hit (redis)", ticker=ticker)
                return json.loads(data)
        except Exception as e:
            logger.warning("Redis cache fetch failed", ticker=ticker, error=str(e))

        logger.info("RAG cache miss", ticker=ticker)
        return None

    async def set_company_context(self, ticker: str, context: Dict):
        """
        Cache company context for fast retrieval.

        Args:
            ticker: Stock ticker symbol
            context: Company context dictionary
        """
        key = f"company_context:{ticker}"
        try:
            await self.redis.setex(
                key,
                self.ttl,
                json.dumps(context)
            )
            logger.info("RAG cache stored", ticker=ticker)
        except Exception as e:
            logger.error("Failed to cache company context", ticker=ticker, error=str(e))

    async def build_company_context(self, ticker: str, company_data: Dict) -> Dict:
        """
        Build comprehensive static context from company data.

        Args:
            ticker: Stock ticker symbol
            company_data: Raw company data from data sources

        Returns:
            Structured company context dictionary
        """
        context = {
            "company_name": company_data.get("name", ticker),
            "sector": company_data.get("sector", "Unknown"),
            "description": company_data.get("business_summary", "No description available"),
            "key_strengths": company_data.get("strengths", []),
            "key_risks": company_data.get("risks", [])
        }

        # Cache it for future use
        await self.set_company_context(ticker, context)

        return context
