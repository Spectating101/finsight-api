"""
Portfolio Analyzer Example
Analyzes a stock portfolio using FinSight API

Usage:
    python portfolio_analyzer.py
"""

from finsight import FinSightClient
from typing import List, Dict
import os


class PortfolioAnalyzer:
    """Analyze stock portfolio financial health"""

    def __init__(self, api_key: str):
        self.client = FinSightClient(api_key=api_key)

    def analyze_stock(self, ticker: str) -> Dict:
        """Analyze a single stock"""
        print(f"\nAnalyzing {ticker}...")

        try:
            # Get key metrics
            metrics = self.client.get_metrics(
                ticker,
                ["revenue", "net_income", "total_assets", "total_debt", "cash"]
            )

            # Get company info
            company = self.client.get_company(ticker)

            # Calculate financial ratios
            metrics_dict = {m.name: m.value for m in metrics}

            profit_margin = (metrics_dict["net_income"] / metrics_dict["revenue"]) * 100
            debt_to_assets = (metrics_dict["total_debt"] / metrics_dict["total_assets"]) * 100

            return {
                "ticker": ticker,
                "name": company.name,
                "sector": company.sector,
                "revenue": metrics_dict["revenue"],
                "net_income": metrics_dict["net_income"],
                "profit_margin": profit_margin,
                "debt_to_assets": debt_to_assets,
                "cash": metrics_dict["cash"],
                "status": "success"
            }

        except Exception as e:
            print(f"  Error: {e}")
            return {"ticker": ticker, "status": "error", "error": str(e)}

    def analyze_portfolio(self, tickers: List[str]):
        """Analyze entire portfolio"""
        print("="*60)
        print("PORTFOLIO ANALYSIS")
        print("="*60)

        results = []
        for ticker in tickers:
            result = self.analyze_stock(ticker)
            results.append(result)

        # Generate report
        self.print_report(results)

        return results

    def print_report(self, results: List[Dict]):
        """Print analysis report"""
        print("\n" + "="*60)
        print("PORTFOLIO SUMMARY")
        print("="*60)

        successful = [r for r in results if r.get("status") == "success"]

        if not successful:
            print("No successful analyses")
            return

        # Print individual stocks
        print(f"\n{'Ticker':<8} {'Company':<30} {'Profit Margin':<15} {'Debt/Assets':<12}")
        print("-"*60)

        for stock in successful:
            print(f"{stock['ticker']:<8} {stock['name'][:28]:<30} "
                  f"{stock['profit_margin']:>12.1f}% {stock['debt_to_assets']:>10.1f}%")

        # Portfolio averages
        avg_profit_margin = sum(s["profit_margin"] for s in successful) / len(successful)
        avg_debt_ratio = sum(s["debt_to_assets"] for s in successful) / len(successful)

        print("\n" + "-"*60)
        print(f"PORTFOLIO AVERAGES:")
        print(f"  Profit Margin: {avg_profit_margin:.1f}%")
        print(f"  Debt/Assets: {avg_debt_ratio:.1f}%")

        # Sector diversification
        sectors = {}
        for stock in successful:
            sector = stock.get("sector", "Unknown")
            sectors[sector] = sectors.get(sector, 0) + 1

        print(f"\nSECTOR DIVERSIFICATION:")
        for sector, count in sorted(sectors.items(), key=lambda x: x[1], reverse=True):
            pct = (count / len(successful)) * 100
            print(f"  {sector}: {count} stocks ({pct:.0f}%)")

        # Red flags
        print(f"\n⚠️  RED FLAGS:")
        high_debt = [s for s in successful if s["debt_to_assets"] > 50]
        low_margin = [s for s in successful if s["profit_margin"] < 5]

        if high_debt:
            print(f"  High debt (>50%): {', '.join(s['ticker'] for s in high_debt)}")

        if low_margin:
            print(f"  Low margins (<5%): {', '.join(s['ticker'] for s in low_margin)}")

        if not high_debt and not low_margin:
            print(f"  ✓ No major red flags detected")


def main():
    # Get API key from environment
    api_key = os.getenv("FINSIGHT_API_KEY", "your_api_key_here")

    # Define portfolio
    portfolio = [
        "AAPL",   # Apple
        "MSFT",   # Microsoft
        "GOOGL",  # Google
        "TSLA",   # Tesla
        "JPM",    # JPMorgan
        "JNJ",    # Johnson & Johnson
        "XOM",    # Exxon
        "WMT",    # Walmart
    ]

    # Analyze portfolio
    analyzer = PortfolioAnalyzer(api_key=api_key)
    analyzer.analyze_portfolio(portfolio)


if __name__ == "__main__":
    main()
