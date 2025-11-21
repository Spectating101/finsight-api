#!/usr/bin/env python3
"""
Simple test script that actually works with Groq API.
Runs 2 experiments to prove the infrastructure works.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from finrobot.experiments.metrics_collector import MetricsCollector
from finrobot.data_source import YFinanceUtils

# Set Groq API key (set this before running)
# export GROQ_API_KEY="your-groq-key-here"
os.environ['OPENAI_API_KEY'] = os.environ.get('GROQ_API_KEY', '')

import openai

def run_simple_experiment(ticker: str, task: str, collector: MetricsCollector):
    """Run a simple RAG-style experiment with Groq."""

    exp_id = f"groq_test_{ticker}_{datetime.now().strftime('%H%M%S')}"

    # Start tracking
    metric = collector.start_measurement(
        experiment_id=exp_id,
        system_name="rag",
        ticker=ticker,
        task_name=task
    )

    try:
        # Get stock data
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - __import__('datetime').timedelta(days=30)).strftime('%Y-%m-%d')

        stock_data = YFinanceUtils.get_stock_data(ticker, start_date, end_date)
        context = f"Stock {ticker} recent data:\n{stock_data.tail(5).to_string()}"

        # Create Groq client
        client = openai.OpenAI(
            api_key=os.environ.get('GROQ_API_KEY'),
            base_url='https://api.groq.com/openai/v1'
        )

        # Make prediction
        prompt = f"{context}\n\nBased on this data, {task}"

        response = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[
                {'role': 'system', 'content': 'You are a financial analyst. Be concise.'},
                {'role': 'user', 'content': prompt}
            ],
            max_tokens=200,
            temperature=0.2
        )

        result = response.choices[0].message.content
        metric.set_response(result)

        # Track usage
        metric.prompt_tokens = response.usage.prompt_tokens
        metric.completion_tokens = response.usage.completion_tokens
        # Groq pricing: ~$0.001/1K tokens
        metric.total_cost = (metric.prompt_tokens + metric.completion_tokens) / 1000 * 0.001

        print(f"\n✓ {ticker} - {task}")
        print(f"  Response: {result[:100]}...")
        print(f"  Latency: {metric.latency_seconds:.2f}s")
        print(f"  Tokens: {response.usage.total_tokens}")

    except Exception as e:
        print(f"\n✗ {ticker} - {task}: {e}")
        metric.error_occurred = True
        metric.error_message = str(e)

    finally:
        collector.end_measurement(metric)

    return metric

if __name__ == '__main__':
    print("="*80)
    print("GROQ API TEST - FinRobot Infrastructure")
    print("="*80)
    print()

    collector = MetricsCollector()

    # Run 4 simple experiments
    experiments = [
        ("AAPL", "predict the price movement for the next week"),
        ("MSFT", "identify the top 2 risk factors"),
        ("GOOGL", "predict the price movement for the next week"),
        ("TSLA", "identify the top 2 risk factors"),
    ]

    results = []
    for ticker, task in experiments:
        metric = run_simple_experiment(ticker, task, collector)
        results.append(metric)

    # Export results
    output_file = collector.export_csv("groq_test_results.csv")
    print(f"\n{'='*80}")
    print(f"Results exported to: {output_file}")
    print(f"Total experiments: {len(results)}")
    print(f"Successful: {sum(1 for r in results if not r.error_occurred)}")
    print(f"Failed: {sum(1 for r in results if r.error_occurred)}")
    print("="*80)
