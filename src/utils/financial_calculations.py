"""
Financial Calculations and Ratios
Compute common financial metrics and ratios from raw SEC data
"""

from typing import Dict, Optional, Any
from decimal import Decimal, InvalidOperation
import structlog

logger = structlog.get_logger(__name__)


class FinancialCalculator:
    """Calculate financial ratios and metrics"""

    @staticmethod
    def safe_divide(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
        """Safely divide two numbers, return None if invalid"""
        if numerator is None or denominator is None:
            return None
        if denominator == 0:
            return None
        try:
            return float(numerator) / float(denominator)
        except (TypeError, ValueError, InvalidOperation):
            return None

    @staticmethod
    def safe_multiply(a: Optional[float], b: Optional[float]) -> Optional[float]:
        """Safely multiply two numbers"""
        if a is None or b is None:
            return None
        try:
            return float(a) * float(b)
        except (TypeError, ValueError):
            return None

    @classmethod
    def calculate_ratios(cls, fundamentals: Dict[str, Any]) -> Dict[str, Optional[float]]:
        """
        Calculate comprehensive financial ratios from fundamentals data

        Args:
            fundamentals: Dictionary with keys like 'revenue', 'netIncome', 'totalAssets', etc.

        Returns:
            Dictionary of calculated ratios
        """
        ratios = {}

        # Extract values (handle None gracefully)
        revenue = fundamentals.get('revenue')
        net_income = fundamentals.get('netIncome')
        total_assets = fundamentals.get('totalAssets')
        total_equity = fundamentals.get('shareholdersEquity')
        current_assets = fundamentals.get('currentAssets')
        current_liabilities = fundamentals.get('currentLiabilities')
        total_debt = fundamentals.get('totalDebt')
        shares_diluted = fundamentals.get('sharesDiluted')
        cost_of_revenue = fundamentals.get('costOfRevenue')
        gross_profit = fundamentals.get('grossProfit')
        operating_income = fundamentals.get('operatingIncome')

        # Profitability Ratios
        ratios['profit_margin'] = cls.safe_divide(net_income, revenue)
        ratios['gross_margin'] = cls.safe_divide(gross_profit, revenue)
        ratios['operating_margin'] = cls.safe_divide(operating_income, revenue)
        ratios['roa'] = cls.safe_divide(net_income, total_assets)  # Return on Assets
        ratios['roe'] = cls.safe_divide(net_income, total_equity)  # Return on Equity

        # Valuation Ratios (need market cap for P/E, P/B)
        market_cap = fundamentals.get('marketCap')
        if market_cap:
            ratios['pe_ratio'] = cls.safe_divide(market_cap, net_income)
            ratios['pb_ratio'] = cls.safe_divide(market_cap, total_equity)
        else:
            # Can't calculate without market cap
            ratios['pe_ratio'] = None
            ratios['pb_ratio'] = None

        # Earnings per share
        ratios['eps_diluted'] = cls.safe_divide(net_income, shares_diluted)

        # Liquidity Ratios
        ratios['current_ratio'] = cls.safe_divide(current_assets, current_liabilities)

        # Quick ratio (current assets - inventory) / current liabilities
        # We don't have inventory separately, so approximate with current assets
        ratios['quick_ratio'] = cls.safe_divide(current_assets, current_liabilities)

        # Leverage Ratios
        ratios['debt_to_equity'] = cls.safe_divide(total_debt, total_equity)
        ratios['debt_to_assets'] = cls.safe_divide(total_debt, total_assets)

        # Asset turnover
        ratios['asset_turnover'] = cls.safe_divide(revenue, total_assets)

        # Round to 4 decimal places for readability
        for key, value in ratios.items():
            if value is not None:
                ratios[key] = round(value, 4)

        return ratios

    @classmethod
    def calculate_growth_rates(cls, current: Dict[str, Any], previous: Dict[str, Any]) -> Dict[str, Optional[float]]:
        """
        Calculate year-over-year growth rates

        Args:
            current: Current period fundamentals
            previous: Previous period fundamentals

        Returns:
            Dictionary of growth rates (as decimals, e.g., 0.15 = 15% growth)
        """
        growth = {}

        metrics = ['revenue', 'netIncome', 'totalAssets', 'shareholdersEquity']

        for metric in metrics:
            current_val = current.get(metric)
            previous_val = previous.get(metric)

            if current_val is not None and previous_val is not None and previous_val != 0:
                growth_rate = (current_val - previous_val) / abs(previous_val)
                growth[f'{metric}_growth'] = round(growth_rate, 4)
            else:
                growth[f'{metric}_growth'] = None

        return growth

    @classmethod
    def calculate_per_share_metrics(cls, fundamentals: Dict[str, Any]) -> Dict[str, Optional[float]]:
        """Calculate per-share metrics"""
        per_share = {}

        shares = fundamentals.get('sharesDiluted') or fundamentals.get('sharesBasic')

        if shares:
            # Book value per share
            equity = fundamentals.get('shareholdersEquity')
            per_share['book_value_per_share'] = cls.safe_divide(equity, shares)

            # Revenue per share
            revenue = fundamentals.get('revenue')
            per_share['revenue_per_share'] = cls.safe_divide(revenue, shares)

            # Cash per share
            cash = fundamentals.get('cashAndEquivalents')
            per_share['cash_per_share'] = cls.safe_divide(cash, shares)

        # Round values
        for key, value in per_share.items():
            if value is not None:
                per_share[key] = round(value, 4)

        return per_share

    @classmethod
    def calculate_all_metrics(cls, fundamentals: Dict[str, Any], previous: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Calculate all available metrics

        Returns comprehensive metrics dictionary
        """
        result = {
            'ratios': cls.calculate_ratios(fundamentals),
            'per_share': cls.calculate_per_share_metrics(fundamentals)
        }

        if previous:
            result['growth'] = cls.calculate_growth_rates(fundamentals, previous)

        return result
