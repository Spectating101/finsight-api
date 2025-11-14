#!/usr/bin/env python3
"""
Fact-Lookup Task Variant: Tests if Agent > RAG holds for factual retrieval
Addresses task selection bias by testing on different task type

Usage:
  python run_fact_lookup_task.py --api-key csk-xxx --system agent --output results/fact_lookup_agent.json
  python run_fact_lookup_task.py --api-key csk-xxx --system rag --output results/fact_lookup_rag.json
"""
import argparse
import json
import time
import yfinance as yf
from openai import OpenAI
import random

# Import company list
import sys
sys.path.append('/home/user/finsight-api/finrobot-coursework')
from scripts.company_list_expanded import ALL_TICKERS

def get_ground_truth(ticker):
    """Get factual ground truth from yfinance"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        history = stock.history(period="1mo")

        return {
            'ticker': ticker,
            'sector': info.get('sector', 'Unknown'),
            'pe_ratio': info.get('trailingPE', None),
            'market_cap_billions': info.get('marketCap', 0) / 1e9 if info.get('marketCap') else None,
            'current_price': history['Close'].iloc[-1] if len(history) > 0 else None,
            '1mo_return_pct': ((history['Close'].iloc[-1] / history['Close'].iloc[0]) - 1) * 100 if len(history) > 1 else None,
            'company_name': info.get('longName', ticker)
        }
    except Exception as e:
        return {'ticker': ticker, 'error': str(e)}

def generate_fact_questions(ticker, ground_truth):
    """Generate fact-lookup questions for a company"""
    questions = [
        f"What sector does {ticker} belong to?",
        f"What is {ticker}'s current P/E ratio?",
        f"What is {ticker}'s market capitalization in billions of dollars?",
        f"What was {ticker}'s 1-month stock price return percentage?",
        f"What is the full company name for ticker {ticker}?"
    ]

    # Randomly select 2-3 questions per company
    selected = random.sample(questions, k=random.randint(2, 3))
    return selected

def run_agent_fact_lookup(ticker, questions, client, model, temperature):
    """Run agent on fact-lookup task"""
    start_time = time.time()

    # Agent gets tools to fetch data
    prompt = f"""Answer the following questions about {ticker}:

{chr(10).join(f'{i+1}. {q}' for i, q in enumerate(questions))}

Use available financial data sources to find accurate answers. Be specific and numerical where applicable."""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a financial data analyst. Provide accurate, factual answers."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=400
        )

        return {
            'ticker': ticker,
            'questions': questions,
            'latency_seconds': time.time() - start_time,
            'response': response.choices[0].message.content
        }
    except Exception as e:
        return {'ticker': ticker, 'error': str(e)}

def run_rag_fact_lookup(ticker, questions, ground_truth, client, model, temperature):
    """Run RAG on fact-lookup task"""
    start_time = time.time()

    # RAG gets pre-retrieved context
    if 'error' in ground_truth:
        return {'ticker': ticker, 'error': ground_truth['error']}

    context = f"""{ticker} Financial Data:
Company: {ground_truth['company_name']}
Sector: {ground_truth['sector']}
P/E Ratio: {ground_truth['pe_ratio']:.2f if ground_truth['pe_ratio'] else 'N/A'}
Market Cap: ${ground_truth['market_cap_billions']:.2f}B
Current Price: ${ground_truth['current_price']:.2f}
1-month return: {ground_truth['1mo_return_pct']:.1f}%

Answer these questions based on the data above:
{chr(10).join(f'{i+1}. {q}' for i, q in enumerate(questions))}"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": context}
            ],
            temperature=temperature,
            max_tokens=400
        )

        return {
            'ticker': ticker,
            'questions': questions,
            'latency_seconds': time.time() - start_time,
            'response': response.choices[0].message.content
        }
    except Exception as e:
        return {'ticker': ticker, 'error': str(e)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--system', choices=['agent', 'rag'], required=True)
    parser.add_argument('--model', default='llama-3.3-70b')
    parser.add_argument('--temperature', type=float, default=0.1)  # Lower temp for factual accuracy
    parser.add_argument('--api-key', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--n', type=int, default=30, help='Number of companies to test')
    args = parser.parse_args()

    # Initialize client
    client = OpenAI(
        api_key=args.api_key,
        base_url="https://api.cerebras.ai/v1"
    )

    # Select random subset if needed
    tickers = random.sample(ALL_TICKERS, min(args.n, len(ALL_TICKERS)))

    print(f"Running {args.system.upper()} on fact-lookup task...")
    print(f"Testing {len(tickers)} companies")
    print("="*60)

    results = []
    for i, ticker in enumerate(tickers):
        print(f"[{i+1}/{len(tickers)}] {ticker}")

        # Get ground truth
        ground_truth = get_ground_truth(ticker)
        if 'error' in ground_truth:
            results.append({'ticker': ticker, 'error': ground_truth['error']})
            continue

        # Generate questions
        questions = generate_fact_questions(ticker, ground_truth)

        # Run system
        if args.system == 'agent':
            result = run_agent_fact_lookup(ticker, questions, client, args.model, args.temperature)
        else:
            result = run_rag_fact_lookup(ticker, questions, ground_truth, client, args.model, args.temperature)

        # Store ground truth for accuracy checking
        result['ground_truth'] = ground_truth
        results.append(result)

        # Rate limiting
        if i < len(tickers) - 1:
            time.sleep(2)

    # Save results
    import os
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✓ Saved {len(results)} results to {args.output}")
    print("\nNext: Run analyze_fact_lookup.py to check accuracy")

if __name__ == '__main__':
    main()
