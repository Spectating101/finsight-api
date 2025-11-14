#!/usr/bin/env python3
"""
Cross-Model Validation: Test if Agent > RAG holds across different LLMs
Tests on GPT-4o-mini, Claude-3.5-Haiku, Llama-3.3-70b

Usage:
  python run_cross_model_validation.py --openai-key sk-xxx --anthropic-key sk-ant-xxx
"""
import argparse
import json
import time
import yfinance as yf
from openai import OpenAI
import anthropic

TICKERS = ['AAPL', 'MSFT', 'JPM', 'TSLA', 'XOM', 'JNJ', 'WMT', 'NVDA', 'BAC', 'CVX']  # 10 companies

def get_company_data(ticker):
    """Get company data using yfinance"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        history = stock.history(period="1mo")

        return {
            'ticker': ticker,
            'price': history['Close'].iloc[-1] if len(history) > 0 else None,
            'name': info.get('longName', ticker),
            'sector': info.get('sector', 'Unknown'),
            'pe': info.get('trailingPE', None),
            '1mo_return': ((history['Close'].iloc[-1] / history['Close'].iloc[0]) - 1) * 100 if len(history) > 1 else None
        }
    except Exception as e:
        return {'ticker': ticker, 'error': str(e)}

def run_agent_openai(ticker, client, model, temperature):
    """Run agent with OpenAI models"""
    start_time = time.time()
    data = get_company_data(ticker)

    if 'error' in data:
        return {'ticker': ticker, 'error': data['error']}

    prompt = f"""Analyze {ticker} and provide:

**Positive Developments** (2-3 key factors)
**Potential Concerns** (2-3 risks)
**Prediction**: Next week movement forecast with justification

Data: Price ${data['price']:.2f}, Sector {data['sector']}, P/E {data['pe']}, 1mo return {data['1mo_return']:.1f}%

Be analytical and specific."""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Financial analyst providing structured analysis."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=600
        )

        return {
            'ticker': ticker,
            'latency_seconds': time.time() - start_time,
            'transcript': f"Analyst:\n\n{response.choices[0].message.content}"
        }
    except Exception as e:
        return {'ticker': ticker, 'error': str(e)}

def run_agent_anthropic(ticker, client, model, temperature):
    """Run agent with Claude models"""
    start_time = time.time()
    data = get_company_data(ticker)

    if 'error' in data:
        return {'ticker': ticker, 'error': data['error']}

    prompt = f"""Analyze {ticker} and provide:

**Positive Developments** (2-3 key factors)
**Potential Concerns** (2-3 risks)
**Prediction**: Next week movement forecast with justification

Data: Price ${data['price']:.2f}, Sector {data['sector']}, P/E {data['pe']}, 1mo return {data['1mo_return']:.1f}%

Be analytical and specific."""

    try:
        response = client.messages.create(
            model=model,
            max_tokens=600,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}]
        )

        return {
            'ticker': ticker,
            'latency_seconds': time.time() - start_time,
            'transcript': f"Analyst:\n\n{response.content[0].text}"
        }
    except Exception as e:
        return {'ticker': ticker, 'error': str(e)}

def run_rag_openai(ticker, client, model, temperature):
    """Run RAG with OpenAI models"""
    start_time = time.time()
    data = get_company_data(ticker)

    if 'error' in data:
        return {'ticker': ticker, 'error': data['error']}

    context = f"""{ticker} Data:
Price: ${data['price']:.2f}
Company: {data['name']}
Sector: {data['sector']}
P/E: {data['pe']}
1-month return: {data['1mo_return']:.1f}%

Analyze and predict next week's movement."""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": context}],
            temperature=temperature,
            max_tokens=500
        )

        return {
            'ticker': ticker,
            'latency_seconds': time.time() - start_time,
            'analysis': response.choices[0].message.content
        }
    except Exception as e:
        return {'ticker': ticker, 'error': str(e)}

def run_rag_anthropic(ticker, client, model, temperature):
    """Run RAG with Claude models"""
    start_time = time.time()
    data = get_company_data(ticker)

    if 'error' in data:
        return {'ticker': ticker, 'error': data['error']}

    context = f"""{ticker} Data:
Price: ${data['price']:.2f}
Company: {data['name']}
Sector: {data['sector']}
P/E: {data['pe']}
1-month return: {data['1mo_return']:.1f}%

Analyze and predict next week's movement."""

    try:
        response = client.messages.create(
            model=model,
            max_tokens=500,
            temperature=temperature,
            messages=[{"role": "user", "content": context}]
        )

        return {
            'ticker': ticker,
            'latency_seconds': time.time() - start_time,
            'analysis': response.content[0].text
        }
    except Exception as e:
        return {'ticker': ticker, 'error': str(e)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--openai-key', help='OpenAI API key (for GPT-4o-mini)')
    parser.add_argument('--anthropic-key', help='Anthropic API key (for Claude)')
    parser.add_argument('--cerebras-key', help='Cerebras API key (for Llama)')
    parser.add_argument('--output-dir', default='scripts/cross_model_results')
    args = parser.parse_args()

    import os
    os.makedirs(args.output_dir, exist_ok=True)

    models_to_test = []

    # GPT-4o-mini (cheap, good)
    if args.openai_key:
        models_to_test.append({
            'name': 'gpt-4o-mini',
            'provider': 'openai',
            'client': OpenAI(api_key=args.openai_key),
            'agent_fn': run_agent_openai,
            'rag_fn': run_rag_openai
        })

    # Claude-3.5-Haiku (fast, cheap)
    if args.anthropic_key:
        models_to_test.append({
            'name': 'claude-3-5-haiku-20241022',
            'provider': 'anthropic',
            'client': anthropic.Anthropic(api_key=args.anthropic_key),
            'agent_fn': run_agent_anthropic,
            'rag_fn': run_rag_anthropic
        })

    # Llama-3.3-70b (baseline from main experiment)
    if args.cerebras_key:
        models_to_test.append({
            'name': 'llama-3.3-70b',
            'provider': 'cerebras',
            'client': OpenAI(api_key=args.cerebras_key, base_url="https://api.cerebras.ai/v1"),
            'agent_fn': run_agent_openai,
            'rag_fn': run_rag_openai
        })

    if not models_to_test:
        print("ERROR: No API keys provided. Use --openai-key, --anthropic-key, or --cerebras-key")
        return

    print(f"Testing {len(models_to_test)} models on {len(TICKERS)} companies...")
    print(f"Models: {[m['name'] for m in models_to_test]}")
    print("="*60)

    for model_config in models_to_test:
        print(f"\nTesting {model_config['name']}...")

        # Run Agent
        print(f"  Running Agent...")
        agent_results = []
        for i, ticker in enumerate(TICKERS):
            print(f"    [{i+1}/{len(TICKERS)}] {ticker}")
            result = model_config['agent_fn'](ticker, model_config['client'], model_config['name'], 0.2)
            agent_results.append(result)
            time.sleep(2)  # Rate limiting

        with open(f"{args.output_dir}/{model_config['name']}_agent.json", 'w') as f:
            json.dump(agent_results, f, indent=2)

        # Run RAG
        print(f"  Running RAG...")
        rag_results = []
        for i, ticker in enumerate(TICKERS):
            print(f"    [{i+1}/{len(TICKERS)}] {ticker}")
            result = model_config['rag_fn'](ticker, model_config['client'], model_config['name'], 0.2)
            rag_results.append(result)
            time.sleep(2)

        with open(f"{args.output_dir}/{model_config['name']}_rag.json", 'w') as f:
            json.dump(rag_results, f, indent=2)

        print(f"  ✓ Saved results for {model_config['name']}")

    print("\n" + "="*60)
    print("✓ Cross-model validation complete!")
    print(f"\nResults saved to {args.output_dir}/")
    print("\nNext: Run analyze_cross_model.py to compare results")

if __name__ == '__main__':
    main()
