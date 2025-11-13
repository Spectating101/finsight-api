#!/usr/bin/env python3
"""
Content Generation Automation
Generates 90 days of blog posts, social media content, and marketing materials
"""

import json
from datetime import datetime, timedelta

# Blog post templates - AI can fill these in
BLOG_POST_TOPICS = [
    {
        "title": "How to Access SEC EDGAR Financial Data via API",
        "slug": "access-sec-edgar-api",
        "keywords": ["SEC EDGAR", "financial data API", "SEC filings"],
        "target_audience": "developers",
        "outline": [
            "What is SEC EDGAR?",
            "Why use an API instead of manual downloads?",
            "Quick start with FinSight API",
            "Code example: Fetch revenue for any company",
            "Advanced: Batch processing multiple companies",
            "Common pitfalls and solutions"
        ]
    },
    {
        "title": "Building a Stock Screener with Python and Financial APIs",
        "slug": "build-stock-screener-python",
        "keywords": ["stock screener", "Python", "financial API", "algorithmic trading"],
        "target_audience": "quant developers",
        "outline": [
            "What is a stock screener?",
            "Setting up your Python environment",
            "Fetching financial metrics via FinSight API",
            "Filtering companies by criteria",
            "Building a dashboard with Streamlit",
            "Scheduling daily updates"
        ]
    },
    {
        "title": "SEC EDGAR XBRL Data: A Developer's Guide",
        "slug": "sec-edgar-xbrl-guide",
        "keywords": ["XBRL", "SEC EDGAR", "financial data", "structured data"],
        "target_audience": "fintech developers",
        "outline": [
            "What is XBRL and why it matters",
            "Understanding SEC filing types (10-K, 10-Q, 8-K)",
            "How to extract structured data from XBRL",
            "Common XBRL concepts and mappings",
            "Using FinSight API to access pre-parsed XBRL",
            "Example: Compare 5 years of revenue data"
        ]
    },
    {
        "title": "Financial Data APIs: Free vs Paid - What's Worth It?",
        "slug": "financial-api-comparison",
        "keywords": ["financial data API", "API comparison", "Alpha Vantage", "IEX Cloud"],
        "target_audience": "startup founders",
        "outline": [
            "Landscape of financial data providers",
            "Free APIs: Alpha Vantage, Yahoo Finance",
            "Paid APIs: FinSight, IEX Cloud, Intrinio",
            "What you actually get with each tier",
            "Citation tracking: Why it matters",
            "ROI calculation for your use case"
        ]
    },
    {
        "title": "Real-Time vs Historical Financial Data: Which Do You Need?",
        "slug": "realtime-vs-historical-data",
        "keywords": ["real-time data", "historical data", "financial API"],
        "target_audience": "fintech builders",
        "outline": [
            "Understanding data latency requirements",
            "Use cases for real-time data",
            "Use cases for historical data",
            "Cost implications of each approach",
            "How to choose for your product",
            "Hybrid approach: Best of both worlds"
        ]
    },
    {
        "title": "How Hedge Funds Use Financial Data APIs",
        "slug": "hedge-funds-financial-apis",
        "keywords": ["hedge fund", "algorithmic trading", "quant", "financial data"],
        "target_audience": "finance professionals",
        "outline": [
            "The quantitative revolution in finance",
            "Data sources hedge funds rely on",
            "Automated trading strategies",
            "Backtesting with historical data",
            "Compliance and audit trails",
            "Why citation tracking matters for regulation"
        ]
    },
    {
        "title": "Building a Fintech Startup: Data Infrastructure 101",
        "slug": "fintech-data-infrastructure",
        "keywords": ["fintech", "startup", "data infrastructure", "API"],
        "target_audience": "founders",
        "outline": [
            "Core data needs for fintech products",
            "Build vs buy decision for financial data",
            "API-first architecture benefits",
            "Scaling considerations",
            "Compliance and data provenance",
            "Case study: How we built FinSight"
        ]
    },
    {
        "title": "Financial Metrics That Matter: Beyond Revenue",
        "slug": "financial-metrics-guide",
        "keywords": ["financial metrics", "KPIs", "fundamental analysis"],
        "target_audience": "analysts",
        "outline": [
            "Income statement metrics",
            "Balance sheet health indicators",
            "Cash flow statement insights",
            "Derived metrics (ROE, debt ratios, etc.)",
            "Industry-specific metrics",
            "How to access all of these via API"
        ]
    },
    {
        "title": "API Rate Limiting: Understanding Financial API Tiers",
        "slug": "api-rate-limiting-guide",
        "keywords": ["rate limiting", "API tiers", "pricing"],
        "target_audience": "developers",
        "outline": [
            "What is rate limiting?",
            "Why financial APIs have rate limits",
            "Calculating your actual needs",
            "Caching strategies to reduce API calls",
            "Batch processing for efficiency",
            "When to upgrade tiers"
        ]
    },
    {
        "title": "Citation-Backed Financial Data: Why It Matters",
        "slug": "citation-backed-financial-data",
        "keywords": ["citations", "data provenance", "SEC filings", "compliance"],
        "target_audience": "compliance professionals",
        "outline": [
            "The data provenance problem",
            "Regulatory requirements for data sources",
            "How FinSight provides citation tracking",
            "Example: Tracing a number to its SEC filing",
            "Audit trail benefits",
            "Building trust with users"
        ]
    }
]

# Social media content calendar (90 days)
TWEET_TEMPLATES = [
    # Educational
    "Did you know? {fact} Learn more about financial APIs: {link}",
    "💡 Pro tip: {tip} #fintech #API #developers",
    "🧵 Thread: {topic} (1/5)",
    "📊 Quick comparison: {comparison}",
    "🎓 Tutorial: {tutorial_title} - {link}",

    # Engagement
    "What financial metric do you use most? Reply below 👇",
    "Building a fintech product? What's your biggest data challenge?",
    "Developers: What would your dream financial API look like?",

    # Product updates
    "🚀 New feature: {feature_name} - {description}",
    "📈 FinSight API now supports {new_capability}",
    "⚡ Performance update: {improvement}",

    # Social proof
    "\"Best financial API for {use_case}\" - {customer_name}",
    "🎉 We just processed our {milestone}th API call!",
    "Join {customer_count}+ developers building with FinSight",

    # Value propositions
    "Other APIs give you numbers. We give you citations. Big difference. 📚",
    "Free tier: 100 API calls/month. No credit card. Start building: {link}",
    "{price}/month for unlimited access to 10K+ companies. See pricing: {link}",
]

# Email sequences
EMAIL_SEQUENCES = {
    "onboarding": [
        {
            "day": 0,
            "subject": "Welcome to FinSight API - Your API key is ready",
            "content": """
Hi {name},

Welcome to FinSight! Your API key is active and ready to use.

Here's your key: {api_key}
(Save this - we only show it once!)

🚀 Quick Start:
curl https://api.finsight.io/v1/metrics?ticker=AAPL&metrics=revenue \\
  -H "X-API-Key: {api_key}"

📚 Documentation: https://api.finsight.io/docs
💬 Questions? Just reply to this email.

Happy building!
- The FinSight Team
            """
        },
        {
            "day": 2,
            "subject": "5 things you can build with FinSight API",
            "content": """
Hi {name},

Hope you're enjoying FinSight! Here are 5 quick projects you can build:

1. 📊 Stock Screener - Filter companies by financial metrics
2. 🎯 Portfolio Tracker - Monitor your investments with real data
3. 📈 Financial Dashboard - Visualize company performance over time
4. 🤖 Trading Bot - Automate trading based on financial indicators
5. 📱 Mobile App - Build iOS/Android apps with financial data

Code examples for all 5: https://github.com/finsight-api/examples

Need help? Just reply!

Best,
FinSight Team
            """
        },
        {
            "day": 7,
            "subject": "You're at {usage}% of your free tier limit",
            "content": """
Hi {name},

Just a heads up - you've used {usage}% of your free tier (100 API calls/month).

Want to keep building? Upgrade to Starter for unlimited access:
- 1,000 API calls/month
- 50 requests/minute
- Access to Yahoo Finance data
- Only $49/month

Upgrade now: {upgrade_link}

Or we'll reset your limit next month automatically.

Best,
FinSight Team
            """
        }
    ],
    "upgrade": [
        {
            "day": 0,
            "subject": "🎉 Welcome to {tier} - Here's what's new",
            "content": """
Hi {name},

Congrats on upgrading to {tier}! 🎉

You now have access to:
{features_list}

Your new limits:
- {api_calls} API calls/month
- {rate_limit} requests/minute

🚀 Try these new features:
{feature_examples}

Questions? Our support team is here to help.

Best,
FinSight Team
            """
        }
    ]
}

# GitHub repository templates
GITHUB_REPOS = [
    {
        "name": "python-stock-analyzer",
        "description": "Analyze stocks using FinSight API - Python",
        "readme": """
# Stock Analyzer with FinSight API

A Python tool to analyze stocks using financial data from FinSight API.

## Features
- Fetch financial metrics for any company
- Compare multiple companies side-by-side
- Calculate financial ratios
- Export to CSV/JSON

## Quick Start
```python
import finsight

api = finsight.Client(api_key="your_key_here")
metrics = api.get_metrics("AAPL", ["revenue", "netIncome", "totalAssets"])
print(metrics)
```

## Installation
```bash
pip install finsight-api requests pandas
```

## Get Your API Key
Sign up free: https://api.finsight.io/register

## Examples
See `examples/` folder for:
- Basic stock screener
- Portfolio tracker
- Financial ratio calculator
- Batch company analysis

## Powered by FinSight API
The only financial API with SEC-grade citations.
        """
    },
    {
        "name": "javascript-financial-dashboard",
        "description": "React dashboard for financial data - JavaScript",
        "readme": """
# Financial Dashboard with FinSight API

Real-time financial dashboard built with React and FinSight API.

## Demo
[Live Demo](https://demo.finsight-dashboard.com)

## Features
- 📊 Real-time financial metrics
- 📈 Interactive charts
- 🔍 Company search
- 📱 Mobile responsive

## Quick Start
```bash
npm install
npm start
```

Set your API key in `.env`:
```
REACT_APP_FINSIGHT_API_KEY=your_key_here
```

## Get Your API Key
Sign up free: https://api.finsight.io/register
        """
    }
]

def generate_content_calendar(start_date, days=90):
    """Generate 90-day content calendar"""
    calendar = []

    for i in range(days):
        date = start_date + timedelta(days=i)

        # Blog posts (2x per week)
        if date.weekday() in [1, 4]:  # Tuesday, Friday
            topic = BLOG_POST_TOPICS[i % len(BLOG_POST_TOPICS)]
            calendar.append({
                "date": date.isoformat(),
                "type": "blog_post",
                "topic": topic["title"],
                "status": "scheduled"
            })

        # Social media (daily)
        calendar.append({
            "date": date.isoformat(),
            "type": "tweet",
            "content": "Generated via AI - see templates",
            "status": "scheduled"
        })

    return calendar

def main():
    print("🤖 Generating Content Automation Package...\n")

    # Generate content calendar
    start_date = datetime.now()
    calendar = generate_content_calendar(start_date)

    # Save to JSON
    output = {
        "generated_at": datetime.now().isoformat(),
        "blog_posts": BLOG_POST_TOPICS,
        "tweet_templates": TWEET_TEMPLATES,
        "email_sequences": EMAIL_SEQUENCES,
        "github_repos": GITHUB_REPOS,
        "content_calendar": calendar
    }

    with open('/home/user/finsight-api/automation/content_automation_package.json', 'w') as f:
        json.dump(output, f, indent=2)

    print("✅ Generated:")
    print(f"   - {len(BLOG_POST_TOPICS)} blog post outlines")
    print(f"   - {len(TWEET_TEMPLATES)} tweet templates")
    print(f"   - {len(EMAIL_SEQUENCES)} email sequences")
    print(f"   - {len(GITHUB_REPOS)} GitHub repository templates")
    print(f"   - 90-day content calendar")
    print(f"\n📁 Saved to: automation/content_automation_package.json")

if __name__ == "__main__":
    main()
