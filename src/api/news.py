"""
Company News Endpoints
Real-time news and press releases via Finnhub
"""

import structlog
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from src.data_sources import get_registry, DataSourceCapability
from src.models.user import User, APIKey
from src.utils.validators import validate_ticker

logger = structlog.get_logger(__name__)
router = APIRouter()


async def get_current_user_from_request(request: Request) -> tuple[User, APIKey]:
    """Get authenticated user from request state"""
    user = getattr(request.state, "user", None)
    api_key = getattr(request.state, "api_key", None)

    if not user or not api_key:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "authentication_required",
                "message": "Valid API key required"
            }
        )

    return user, api_key


class NewsItem(BaseModel):
    """Single news item"""
    date: str
    headline: str
    summary: str
    source: str
    url: Optional[str] = None
    image: Optional[str] = None
    category: Optional[str] = None


class CompanyNewsResponse(BaseModel):
    """Company news response"""
    ticker: str
    news: List[NewsItem]
    start_date: str
    end_date: str
    count: int
    source: str = "Finnhub"


@router.get("/company/{ticker}/news", response_model=CompanyNewsResponse)
async def get_company_news(
    ticker: str,
    days: int = Query(7, description="Number of days of news to retrieve", ge=1, le=30),
    max_news: int = Query(10, description="Maximum number of news items", ge=1, le=50),
    auth: tuple[User, APIKey] = Depends(get_current_user_from_request)
):
    """
    Get company news and press releases

    **Required Tier:** Free+

    Returns recent company news from Finnhub.

    **Example:**
    ```
    GET /api/v1/company/AAPL/news?days=7&max_news=10
    ```

    **Returns:**
    List of news items with headlines, summaries, and source URLs

    **Benefits:**
    - Real-time company news
    - Press releases and announcements
    - Sentiment analysis ready (headlines + summaries)
    - Source attribution and URLs
    """
    user, _ = auth

    try:
        # Validate ticker
        ticker = validate_ticker(ticker)

        # Get news-capable sources
        registry = get_registry()
        sources = registry.get_by_capability(DataSourceCapability.NEWS)

        if not sources:
            raise HTTPException(
                status_code=503,
                detail="News data source not available"
            )

        # Use Finnhub source
        finnhub_source = next((s for s in sources if "finnhub" in str(type(s)).lower()), None)

        if not finnhub_source:
            raise HTTPException(
                status_code=503,
                detail="Finnhub news source not available"
            )

        # Calculate date range
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        # Get news
        news_data = await finnhub_source.get_company_news(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            max_news=max_news
        )

        if not news_data:
            logger.info("No news found", ticker=ticker, days=days)
            news_data = []

        # Format response
        news_items = [
            NewsItem(
                date=item["date"],
                headline=item["headline"],
                summary=item["summary"],
                source=item.get("source", "Unknown"),
                url=item.get("url"),
                image=item.get("image"),
                category=item.get("category")
            )
            for item in news_data
        ]

        logger.info(
            "Company news fetched",
            user_id=user.user_id,
            ticker=ticker,
            news_count=len(news_items)
        )

        return CompanyNewsResponse(
            ticker=ticker.upper(),
            news=news_items,
            start_date=start_date,
            end_date=end_date,
            count=len(news_items)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch company news", ticker=ticker, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch company news"
        )
