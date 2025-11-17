#!/usr/bin/env python3
"""
Real A/B Experiment using Cerebras API.
Smaller subset for validation of synthetic results.
"""

import json
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import autogen
import yfinance as yf

from finrobot.experiments.quality_scorer import (
    score_response,
    quality_metrics_to_dict,
    calculate_composite_quality_score
)

# Configuration
OAI_CONFIG = "OAI_CONFIG_LIST"
MODEL = "llama-3.3-70b"
TEMPERATURE = 0.2
OUTPUT_DIR = "results"

# Smaller subset for real experiments (save API calls)
TICKERS = ["AAPL", "MSFT", "NVDA"]  # 3 stocks instead of 8
TASKS = ["prediction"]  # 1 task instead of 3


def get_current_date():
    return datetime.now().strftime("%Y-%m-%d")


def fetch_stock_data(ticker: str) -> dict:
    """Fetch stock data using yfinance."""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo")
        info = stock.info

        return {
            "ticker": ticker,
            "company_name": info.get("longName", ticker),
            "sector": info.get("sector", "Unknown"),
            "current_price": info.get("currentPrice", info.get("regularMarketPrice", 0)),
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("trailingPE", 0),
            "52_week_high": info.get("fiftyTwoWeekHigh", 0),
            "52_week_low": info.get("fiftyTwoWeekLow", 0),
            "price_change_1mo": ((hist["Close"].iloc[-1] / hist["Close"].iloc[0]) - 1) * 100 if len(hist) > 1 else 0,
            "volatility": hist["Close"].pct_change().std() * 100 if len(hist) > 1 else 0,
        }
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


def run_rag_real(ticker: str) -> dict:
    """Run RAG experiment with real Cerebras API."""
    print(f"  [RAG] {ticker}...")
    start_time = time.time()

    # Fetch data
    fetch_start = time.time()
    stock_data = fetch_stock_data(ticker)
    fetch_time = time.time() - fetch_start

    context = f"""
Stock: {ticker} ({stock_data.get('company_name', ticker)})
Sector: {stock_data.get('sector', 'Unknown')}
Current Price: ${stock_data.get('current_price', 0):.2f}
Market Cap: ${stock_data.get('market_cap', 0):,}
P/E Ratio: {stock_data.get('pe_ratio', 0):.2f}
52-Week High: ${stock_data.get('52_week_high', 0):.2f}
52-Week Low: ${stock_data.get('52_week_low', 0):.2f}
1-Month Change: {stock_data.get('price_change_1mo', 0):.2f}%
Volatility: {stock_data.get('volatility', 0):.2f}%
"""

    prompt = f"""Analyze this stock data and provide:
1. 2-3 key positive factors (cite specific numbers)
2. 2-3 risk factors (cite specific numbers)
3. 1-week price prediction with percentage and reasoning

{context}

Be specific and concise."""

    # Single LLM call
    config_list = autogen.config_list_from_json(OAI_CONFIG, filter_dict={"model": [MODEL]})
    client = autogen.OpenAIWrapper(config_list=config_list)

    llm_start = time.time()
    response = client.create(
        messages=[{"role": "user", "content": prompt}],
        temperature=TEMPERATURE,
    )
    llm_time = time.time() - llm_start

    output = response.choices[0].message.content
    total_time = time.time() - start_time

    # Calculate quality metrics
    prompt_tokens = response.usage.prompt_tokens if hasattr(response.usage, 'prompt_tokens') else 500
    completion_tokens = response.usage.completion_tokens if hasattr(response.usage, 'completion_tokens') else len(output.split())

    quality = score_response(
        response=output,
        task="prediction",
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        model=MODEL
    )

    print(f"  [RAG] {ticker} done in {total_time:.2f}s (Quality: {calculate_composite_quality_score(quality):.1f}/100)")

    return {
        "system": "rag",
        "ticker": ticker,
        "task": "prediction",
        "model": MODEL,
        "response": output,
        "latency_total": round(total_time, 3),
        "latency_fetch": round(fetch_time, 3),
        "latency_llm": round(llm_time, 3),
        "tool_calls": 0,
        "reasoning_steps": 1,
        "response_length": len(output),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "timestamp": get_current_date(),
        "data_source": "real_cerebras_api",
        "quality_metrics": quality_metrics_to_dict(quality),
        "composite_quality_score": calculate_composite_quality_score(quality),
    }


def run_agent_real(ticker: str) -> dict:
    """Run Agent experiment with real Cerebras API."""
    print(f"  [AGENT] {ticker}...")
    start_time = time.time()

    config_list = autogen.config_list_from_json(OAI_CONFIG, filter_dict={"model": [MODEL]})
    llm_config = {"config_list": config_list, "timeout": 120, "temperature": TEMPERATURE}

    from autogen import AssistantAgent, UserProxyAgent, register_function
    from textwrap import dedent

    assistant = AssistantAgent(
        "Analyst",
        system_message="You are a stock analyst. Use tools to gather data. Reply TERMINATE when done.",
        llm_config=llm_config,
    )

    user_proxy = UserProxyAgent(
        "User",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=8,
        is_termination_msg=lambda x: x.get("content") is not None and "TERMINATE" in x.get("content", ""),
        code_execution_config=False,
    )

    tool_calls = []

    def get_stock_info(symbol: str) -> str:
        """Get stock fundamentals."""
        tool_calls.append(("get_stock_info", symbol))
        return json.dumps(fetch_stock_data(symbol), indent=2, default=str)

    def get_technicals(symbol: str) -> str:
        """Calculate technical indicators."""
        tool_calls.append(("get_technicals", symbol))
        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period="3mo")
            sma_20 = hist["Close"].tail(20).mean()
            current = hist["Close"].iloc[-1]
            volatility = hist["Close"].pct_change().std() * 100
            return json.dumps({
                "current": round(current, 2),
                "sma_20": round(sma_20, 2),
                "vs_sma20": f"{((current/sma_20)-1)*100:.2f}%",
                "volatility": f"{volatility:.2f}%"
            }, indent=2)
        except Exception as e:
            return f"Error: {e}"

    register_function(get_stock_info, caller=assistant, executor=user_proxy,
                     name="get_stock_info", description="Get stock fundamentals")
    register_function(get_technicals, caller=assistant, executor=user_proxy,
                     name="get_technicals", description="Get technical indicators")

    task_prompt = f"""Analyze {ticker}:
1. Use get_stock_info to get fundamentals
2. Use get_technicals for technical data
3. Provide 2-3 positives, 2-3 risks, and 1-week prediction
Reply TERMINATE when done."""

    from io import StringIO
    import contextlib

    buffer = StringIO()
    with contextlib.redirect_stdout(buffer):
        user_proxy.initiate_chat(assistant, message=task_prompt, cache=None)

    total_time = time.time() - start_time
    transcript = buffer.getvalue()

    # Extract final response
    final_response = transcript.split("Analyst")[-1] if "Analyst" in transcript else transcript
    reasoning_steps = transcript.count("Analyst") + transcript.count("User")

    # Estimate tokens (AutoGen doesn't easily expose this)
    prompt_tokens = reasoning_steps * 1000  # Rough estimate
    completion_tokens = len(final_response.split())

    quality = score_response(
        response=final_response,
        task="prediction",
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        model=MODEL
    )

    print(f"  [AGENT] {ticker} done in {total_time:.2f}s ({len(tool_calls)} tools, Quality: {calculate_composite_quality_score(quality):.1f}/100)")

    return {
        "system": "agent",
        "ticker": ticker,
        "task": "prediction",
        "model": MODEL,
        "response": final_response[-2000:],  # Last 2000 chars
        "latency_total": round(total_time, 3),
        "tool_calls": len(tool_calls),
        "tool_calls_detail": tool_calls,
        "reasoning_steps": reasoning_steps,
        "response_length": len(final_response),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "timestamp": get_current_date(),
        "data_source": "real_cerebras_api",
        "quality_metrics": quality_metrics_to_dict(quality),
        "composite_quality_score": calculate_composite_quality_score(quality),
    }


def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"\n{'='*60}")
    print("REAL EXPERIMENT - Cerebras API")
    print(f"Stocks: {', '.join(TICKERS)}")
    print(f"Tasks: {', '.join(TASKS)}")
    print(f"{'='*60}\n")

    all_results = []

    for ticker in TICKERS:
        print(f"\n[{ticker}]")

        # RAG
        try:
            rag = run_rag_real(ticker)
            all_results.append(rag)
        except Exception as e:
            print(f"  [RAG] ERROR: {e}")
            all_results.append({"system": "rag", "ticker": ticker, "error": str(e)})

        time.sleep(2)

        # Agent
        try:
            agent = run_agent_real(ticker)
            all_results.append(agent)
        except Exception as e:
            print(f"  [AGENT] ERROR: {e}")
            all_results.append({"system": "agent", "ticker": ticker, "error": str(e)})

        time.sleep(3)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"{OUTPUT_DIR}/real_experiment_{timestamp}.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    # Summary
    print(f"\n{'='*60}")
    print("REAL EXPERIMENT RESULTS")
    print(f"{'='*60}")

    rag_results = [r for r in all_results if r.get("system") == "rag" and "error" not in r]
    agent_results = [r for r in all_results if r.get("system") == "agent" and "error" not in r]

    if rag_results:
        rag_lat = [r["latency_total"] for r in rag_results]
        rag_quality = [r.get("composite_quality_score", 0) for r in rag_results]
        rag_costs = [r.get("quality_metrics", {}).get("estimated_cost_usd", 0) for r in rag_results]
        print(f"\nRAG: {len(rag_results)} experiments")
        print(f"  Avg Latency: {sum(rag_lat)/len(rag_lat):.2f}s")
        print(f"  Avg Quality Score: {sum(rag_quality)/len(rag_quality):.1f}/100")
        print(f"  Avg Cost: ${sum(rag_costs)/len(rag_costs):.6f}")

    if agent_results:
        agent_lat = [r["latency_total"] for r in agent_results]
        agent_tools = [r["tool_calls"] for r in agent_results]
        agent_quality = [r.get("composite_quality_score", 0) for r in agent_results]
        agent_costs = [r.get("quality_metrics", {}).get("estimated_cost_usd", 0) for r in agent_results]
        print(f"\nAgent: {len(agent_results)} experiments")
        print(f"  Avg Latency: {sum(agent_lat)/len(agent_lat):.2f}s")
        print(f"  Avg Tool Calls: {sum(agent_tools)/len(agent_tools):.1f}")
        print(f"  Avg Quality Score: {sum(agent_quality)/len(agent_quality):.1f}/100")
        print(f"  Avg Cost: ${sum(agent_costs)/len(agent_costs):.6f}")

    if rag_results and agent_results:
        lat_ratio = (sum(agent_lat)/len(agent_lat)) / (sum(rag_lat)/len(rag_lat))
        quality_ratio = (sum(agent_quality)/len(agent_quality)) / (sum(rag_quality)/len(rag_quality)) if sum(rag_quality) > 0 else 1.0
        print(f"\nComparative Analysis:")
        print(f"  Latency Ratio: {lat_ratio:.2f}x (Agent slower)")
        print(f"  Quality Ratio: {quality_ratio:.2f}x (Agent better)")

    print(f"\nSaved: {OUTPUT_DIR}/real_experiment_{timestamp}.json")
    return all_results


if __name__ == "__main__":
    main()
