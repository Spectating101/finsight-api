#!/usr/bin/env python3
"""
Expanded company list for publication-quality sample size
30 companies across 6 sectors for statistical significance
"""

# 30 companies selected for:
# 1. Sector diversity (6 sectors × 5 companies each)
# 2. Market cap diversity (large, mid, small cap mix)
# 3. Volatility diversity (stable vs volatile)
# 4. Data availability (all have good yfinance coverage)

COMPANIES = {
    "Technology": [
        "AAPL",  # Apple - Large cap, stable
        "MSFT",  # Microsoft - Large cap, stable
        "GOOGL", # Alphabet - Large cap, stable
        "NVDA",  # NVIDIA - Large cap, high volatility
        "AMD",   # AMD - Mid cap, high volatility
    ],

    "Finance": [
        "JPM",   # JPMorgan - Large cap bank
        "BAC",   # Bank of America - Large cap bank
        "WFC",   # Wells Fargo - Large cap bank
        "GS",    # Goldman Sachs - Investment bank
        "MS",    # Morgan Stanley - Investment bank
    ],

    "Energy": [
        "XOM",   # Exxon Mobil - Large cap oil
        "CVX",   # Chevron - Large cap oil
        "COP",   # ConocoPhillips - Large cap oil
        "SLB",   # Schlumberger - Services
        "OXY",   # Occidental Petroleum - Mid cap
    ],

    "Healthcare": [
        "JNJ",   # Johnson & Johnson - Large cap pharma
        "UNH",   # UnitedHealth - Insurance
        "PFE",   # Pfizer - Large cap pharma
        "ABBV",  # AbbVie - Mid cap pharma
        "TMO",   # Thermo Fisher - Life sciences
    ],

    "Consumer": [
        "TSLA",  # Tesla - High volatility auto
        "WMT",   # Walmart - Large cap retail
        "HD",    # Home Depot - Large cap retail
        "NKE",   # Nike - Apparel
        "MCD",   # McDonald's - Food service
    ],

    "Industrials": [
        "BA",    # Boeing - Aerospace
        "CAT",   # Caterpillar - Heavy machinery
        "GE",    # General Electric - Conglomerate
        "UPS",   # United Parcel Service - Logistics
        "HON",   # Honeywell - Diversified industrial
    ]
}

# Flatten to list
ALL_TICKERS = [ticker for sector in COMPANIES.values() for ticker in sector]

# Task templates
TASKS = {
    "prediction": """Use all tools available to retrieve information for {ticker}.
Analyze the positive developments and potential concerns (2-4 factors each, concise).
Make a rough prediction (e.g., up/down by 2-3%) of the stock price movement
for next week with supporting analysis.""",

    "fact_lookup": """What was {ticker}'s total revenue in the most recent quarter?
Provide the exact dollar amount with the filing date and citation.""",

    "comparison": """Compare {ticker}'s profit margin to the industry average.
Is it above or below average, and by how much?"""
}

if __name__ == '__main__':
    print(f"Total companies: {len(ALL_TICKERS)}")
    print(f"Sectors: {len(COMPANIES)}")
    print(f"\nCompanies by sector:")
    for sector, tickers in COMPANIES.items():
        print(f"  {sector}: {', '.join(tickers)}")
    print(f"\nAll tickers: {' '.join(ALL_TICKERS)}")
