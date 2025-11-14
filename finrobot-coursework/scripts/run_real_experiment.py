#!/usr/bin/env python3
"""
Simplified real experiment runner using direct OpenAI API
No complex dependencies - just openai + yfinance
"""
import json
import time
import argparse
import yfinance as yf
from openai import OpenAI
from datetime import datetime

def get_company_data(ticker):
    """Get company data using yfinance"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        news = stock.news[:5] if hasattr(stock, 'news') else []
        history = stock.history(period="1mo")

        return {
            'ticker': ticker,
            'current_price': history['Close'].iloc[-1] if len(history) > 0 else None,
            'company_name': info.get('longName', ticker),
            'sector': info.get('sector', 'Unknown'),
            'pe_ratio': info.get('trailingPE', None),
            'market_cap': info.get('marketCap', None),
            'news': [n.get('title', '') for n in news[:3]],
            '1mo_return': ((history['Close'].iloc[-1] / history['Close'].iloc[0]) - 1) * 100 if len(history) > 1 else None
        }
    except Exception as e:
        return {'ticker': ticker, 'error': str(e)}

def run_agent(ticker, client, model, temperature):
    """Run agent with real API"""
    start_time = time.time()

    # Get data
    data = get_company_data(ticker)
    if 'error' in data:
        return {'ticker': ticker, 'error': data['error']}

    # Build prompt
    prompt = f"""Analyze {ticker} ({data['company_name']}) and provide:

**Positive Developments** (2-4 key factors):
**Potential Concerns** (2-3 key risks):
**Prediction**: Forecast stock movement for next week (e.g., up/down 3-5%) with justification.

Available data:
- Current price: ${data['current_price']:.2f}
- Sector: {data['sector']}
- P/E Ratio: {data['pe_ratio']}
- 1-month return: {data['1mo_return']:.1f}%
- Recent news: {', '.join(data['news'][:2])}

Be specific and analytical."""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a financial analyst providing structured stock analysis."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=800
        )

        latency = time.time() - start_time
        transcript = f"Market_Analyst (to User_Proxy):\n\n{response.choices[0].message.content}"

        return {
            'ticker': ticker,
            'latency_seconds': latency,
            'transcript': transcript
        }
    except Exception as e:
        return {'ticker': ticker, 'error': str(e)}

def run_rag(ticker, client, model, temperature):
    """Run RAG with real API"""
    start_time = time.time()

    # Get data
    data = get_company_data(ticker)
    if 'error' in data:
        return {'ticker': ticker, 'error': data['error']}

    # RAG style: dump all data then ask for analysis
    context = f"""{ticker} Financial Data:

Price: ${data['current_price']:.2f}
Company: {data['company_name']}
Sector: {data['sector']}
P/E Ratio: {data['pe_ratio']}
Market Cap: ${data['market_cap']/1e9:.1f}B
1-month performance: {data['1mo_return']:.1f}%

Recent News:
{chr(10).join(f'- {n}' for n in data['news'][:3])}

Analyze this stock and predict next week's movement."""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": context}
            ],
            temperature=temperature,
            max_tokens=600
        )

        latency = time.time() - start_time
        analysis = response.choices[0].message.content

        return {
            'ticker': ticker,
            'latency_seconds': latency,
            'analysis': analysis
        }
    except Exception as e:
        return {'ticker': ticker, 'error': str(e)}

def run_zeroshot(ticker, client, model, temperature):
    """Run zero-shot with real API"""
    start_time = time.time()

    prompt = f"Based on general knowledge, briefly analyze {ticker} stock and predict its movement for next week. No external data access."

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=300
        )

        latency = time.time() - start_time
        analysis = response.choices[0].message.content

        return {
            'ticker': ticker,
            'latency_seconds': latency,
            'analysis': analysis
        }
    except Exception as e:
        return {'ticker': ticker, 'error': str(e)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('tickers', nargs='+', help='Stock tickers to analyze')
    parser.add_argument('--system', choices=['agent', 'rag', 'zeroshot'], required=True)
    parser.add_argument('--model', default='llama-3.3-70b')
    parser.add_argument('--temperature', type=float, default=0.2)
    parser.add_argument('--api-key', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    # Initialize client
    client = OpenAI(
        api_key=args.api_key,
        base_url="https://api.cerebras.ai/v1"
    )

    results = []
    for i, ticker in enumerate(args.tickers):
        print(f"[{i+1}/{len(args.tickers)}] Processing {ticker} ({args.system})...")

        if args.system == 'agent':
            result = run_agent(ticker, client, args.model, args.temperature)
        elif args.system == 'rag':
            result = run_rag(ticker, client, args.model, args.temperature)
        else:
            result = run_zeroshot(ticker, client, args.model, args.temperature)

        results.append(result)

        # Rate limiting
        if i < len(args.tickers) - 1:
            time.sleep(3)  # 3 second delay between calls

    # Save results
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✓ Saved {len(results)} results to {args.output}")

if __name__ == '__main__':
    main()
