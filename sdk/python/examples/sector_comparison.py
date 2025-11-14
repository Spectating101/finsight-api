"""
Sector Comparison Example
Compare companies within the same sector

Usage:
    python sector_comparison.py
"""

import asyncio
from finsight import AsyncFinSightClient
import os


async def compare_sector(client, sector_name: str, tickers: list):
    """Compare companies in a sector"""
    print(f"\n{'='*60}")
    print(f"SECTOR: {sector_name}")
    print(f"{'='*60}\n")

    # Fetch metrics for all companies concurrently
    tasks = [
        client.get_metrics(ticker, ["revenue", "net_income"])
        for ticker in tickers
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    companies = []
    for ticker, metrics in zip(tickers, results):
        if isinstance(metrics, Exception):
            print(f"{ticker}: Error - {metrics}")
            continue

        metrics_dict = {m.name: m.value for m in metrics}
        profit_margin = (metrics_dict["net_income"] / metrics_dict["revenue"]) * 100

        companies.append({
            "ticker": ticker,
            "revenue": metrics_dict["revenue"],
            "net_income": metrics_dict["net_income"],
            "profit_margin": profit_margin
        })

    # Sort by revenue
    companies.sort(key=lambda x: x["revenue"], reverse=True)

    # Print results
    print(f"{'Rank':<6} {'Ticker':<8} {'Revenue':<20} {'Net Income':<20} {'Margin':<10}")
    print("-"*60)

    for i, company in enumerate(companies, 1):
        print(f"{i:<6} {company['ticker']:<8} "
              f"${company['revenue']/1e9:>16.1f}B "
              f"${company['net_income']/1e9:>16.1f}B "
              f"{company['profit_margin']:>8.1f}%")

    # Summary stats
    if companies:
        avg_margin = sum(c["profit_margin"] for c in companies) / len(companies)
        print(f"\nAverage profit margin: {avg_margin:.1f}%")

        best_margin = max(companies, key=lambda x: x["profit_margin"])
        print(f"Best margin: {best_margin['ticker']} ({best_margin['profit_margin']:.1f}%)")


async def main():
    api_key = os.getenv("FINSIGHT_API_KEY", "your_api_key_here")

    # Define sectors to compare
    sectors = {
        "Technology": ["AAPL", "MSFT", "GOOGL", "NVDA", "AMD"],
        "Finance": ["JPM", "BAC", "WFC", "GS", "MS"],
        "Energy": ["XOM", "CVX", "COP", "SLB", "OXY"],
        "Healthcare": ["JNJ", "UNH", "PFE", "ABBV", "TMO"]
    }

    async with AsyncFinSightClient(api_key=api_key) as client:
        for sector_name, tickers in sectors.items():
            await compare_sector(client, sector_name, tickers)
            await asyncio.sleep(1)  # Be nice to the API


if __name__ == "__main__":
    asyncio.run(main())
