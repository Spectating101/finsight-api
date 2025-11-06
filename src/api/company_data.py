"""
Company Data Endpoints - High-value aggregated data
Ratios, overviews, and batch endpoints for easy consumption
"""

import structlog
from fastapi import APIRouter, Request, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from src.data_sources import get_registry, DataSourceCapability
from src.models.user import User, APIKey
from src.utils.validators import validate_ticker
from src.utils.financial_calculations import FinancialCalculator

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


class FinancialRatiosResponse(BaseModel):
    """Financial ratios for a company"""
    ticker: str
    as_of_date: Optional[str] = None
    ratios: Dict[str, Optional[float]]
    source: str = "SEC EDGAR"


class CompanyOverviewResponse(BaseModel):
    """Comprehensive company overview in a single response"""
    ticker: str
    company_name: Optional[str] = None
    cik: Optional[str] = None

    fundamentals: Dict[str, Any]
    ratios: Dict[str, Optional[float]]
    per_share_metrics: Dict[str, Optional[float]]

    as_of_date: Optional[str] = None
    source: str = "SEC EDGAR"


class BatchCompanyData(BaseModel):
    """Single company data in batch response"""
    ticker: str
    fundamentals: Optional[Dict[str, Any]] = None
    ratios: Optional[Dict[str, Optional[float]]] = None
    error: Optional[str] = None


class BatchCompaniesResponse(BaseModel):
    """Batch response for multiple companies"""
    companies: List[BatchCompanyData]
    requested: int
    successful: int
    failed: int


async def fetch_company_fundamentals(ticker: str) -> Optional[Dict[str, Any]]:
    """Fetch fundamentals for a company from data sources"""
    try:
        registry = get_registry()
        sources = registry.get_by_capability(DataSourceCapability.FUNDAMENTALS)

        if not sources:
            return None

        source = sources[0]

        # Common metrics to fetch
        metrics = [
            'revenue', 'netIncome', 'totalAssets', 'currentAssets',
            'currentLiabilities', 'shareholdersEquity', 'totalDebt',
            'cashAndEquivalents', 'costOfRevenue', 'grossProfit',
            'operatingIncome', 'sharesDiluted', 'sharesBasic'
        ]

        results = await source.get_financial_data(
            ticker=ticker,
            concepts=metrics,
            period=None  # Get latest
        )

        if not results:
            return None

        # Convert to dictionary
        fundamentals = {}
        as_of_date = None

        for result in results:
            fundamentals[result.concept] = result.value
            if not as_of_date and result.period:
                as_of_date = result.period

        fundamentals['as_of_date'] = as_of_date
        return fundamentals

    except Exception as e:
        logger.error("Failed to fetch fundamentals", ticker=ticker, error=str(e))
        return None


@router.get("/company/{ticker}/ratios", response_model=FinancialRatiosResponse)
async def get_financial_ratios(
    ticker: str,
    auth: tuple[User, APIKey] = Depends(get_current_user_from_request)
):
    """
    Get pre-calculated financial ratios for a company

    **Required Tier:** Free+

    Calculates common financial ratios from SEC EDGAR data:
    - Profitability: profit_margin, gross_margin, operating_margin, ROA, ROE
    - Valuation: P/E ratio, P/B ratio, EPS
    - Liquidity: current_ratio, quick_ratio
    - Leverage: debt_to_equity, debt_to_assets
    - Efficiency: asset_turnover

    **Example:**
    ```
    GET /api/v1/company/AAPL/ratios
    ```

    **Returns:**
    Pre-calculated financial ratios with latest available data
    """
    user, _ = auth

    try:
        # Validate ticker
        ticker = validate_ticker(ticker)

        # Fetch fundamentals
        fundamentals = await fetch_company_fundamentals(ticker)

        if not fundamentals:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for ticker {ticker}"
            )

        # Calculate ratios
        calculator = FinancialCalculator()
        ratios = calculator.calculate_ratios(fundamentals)

        as_of_date = fundamentals.get('as_of_date')

        logger.info(
            "Financial ratios calculated",
            user_id=user.user_id,
            ticker=ticker,
            ratios_count=len([r for r in ratios.values() if r is not None])
        )

        return FinancialRatiosResponse(
            ticker=ticker,
            as_of_date=as_of_date,
            ratios=ratios
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to calculate ratios", ticker=ticker, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to calculate financial ratios"
        )


@router.get("/company/{ticker}/overview", response_model=CompanyOverviewResponse)
async def get_company_overview(
    ticker: str,
    auth: tuple[User, APIKey] = Depends(get_current_user_from_request)
):
    """
    Get comprehensive company overview (fundamentals + ratios + per-share metrics)

    **Required Tier:** Free+

    Returns everything in a single API call:
    - All fundamental metrics (revenue, net income, assets, etc.)
    - All financial ratios (P/E, ROE, debt/equity, etc.)
    - Per-share metrics (EPS, book value, revenue per share)

    **Example:**
    ```
    GET /api/v1/company/AAPL/overview
    ```

    **Returns:**
    Complete company financial snapshot in one response

    **Benefits:**
    - Saves multiple API calls (would need 3+ separate endpoints otherwise)
    - All data from same period (consistency)
    - Ready-to-display data for dashboards
    """
    user, _ = auth

    try:
        # Validate ticker
        ticker = validate_ticker(ticker)

        # Fetch fundamentals
        fundamentals = await fetch_company_fundamentals(ticker)

        if not fundamentals:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for ticker {ticker}"
            )

        as_of_date = fundamentals.pop('as_of_date', None)

        # Calculate all metrics
        calculator = FinancialCalculator()
        ratios = calculator.calculate_ratios(fundamentals)
        per_share = calculator.calculate_per_share_metrics(fundamentals)

        logger.info(
            "Company overview generated",
            user_id=user.user_id,
            ticker=ticker
        )

        return CompanyOverviewResponse(
            ticker=ticker,
            fundamentals=fundamentals,
            ratios=ratios,
            per_share_metrics=per_share,
            as_of_date=as_of_date
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to generate overview", ticker=ticker, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to generate company overview"
        )


@router.get("/batch/companies", response_model=BatchCompaniesResponse)
async def get_batch_companies(
    tickers: str = Query(..., description="Comma-separated list of ticker symbols"),
    include_ratios: bool = Query(True, description="Include calculated ratios"),
    auth: tuple[User, APIKey] = Depends(get_current_user_from_request)
):
    """
    Get data for multiple companies in a single API call

    **Required Tier:** Free+

    Fetch fundamentals and ratios for multiple companies at once.

    **Example:**
    ```
    GET /api/v1/batch/companies?tickers=AAPL,GOOGL,MSFT,TSLA&include_ratios=true
    ```

    **Returns:**
    Array of company data with fundamentals and optionally ratios

    **Benefits:**
    - Save API calls (1 call instead of N calls)
    - Faster response time (parallel fetching)
    - Ideal for portfolio tracking, screeners, watchlists

    **Limits:**
    - Max 20 companies per batch request
    - Failed tickers don't block successful ones
    """
    user, _ = auth

    try:
        # Parse and validate tickers
        ticker_list = [t.strip().upper() for t in tickers.split(",")]

        # Limit to 20 companies
        if len(ticker_list) > 20:
            raise HTTPException(
                status_code=400,
                detail="Too many tickers (max 20 per batch request)"
            )

        # Validate each ticker
        try:
            ticker_list = [validate_ticker(t) for t in ticker_list]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Fetch data for each company
        companies = []
        successful = 0
        failed = 0

        calculator = FinancialCalculator()

        for ticker in ticker_list:
            try:
                fundamentals = await fetch_company_fundamentals(ticker)

                if fundamentals:
                    fundamentals.pop('as_of_date', None)

                    ratios = None
                    if include_ratios:
                        ratios = calculator.calculate_ratios(fundamentals)

                    companies.append(BatchCompanyData(
                        ticker=ticker,
                        fundamentals=fundamentals,
                        ratios=ratios
                    ))
                    successful += 1
                else:
                    companies.append(BatchCompanyData(
                        ticker=ticker,
                        error="No data found"
                    ))
                    failed += 1

            except Exception as e:
                logger.error("Batch fetch failed for ticker", ticker=ticker, error=str(e))
                companies.append(BatchCompanyData(
                    ticker=ticker,
                    error=str(e)
                ))
                failed += 1

        logger.info(
            "Batch companies fetched",
            user_id=user.user_id,
            requested=len(ticker_list),
            successful=successful,
            failed=failed
        )

        return BatchCompaniesResponse(
            companies=companies,
            requested=len(ticker_list),
            successful=successful,
            failed=failed
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Batch request failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to process batch request"
        )
