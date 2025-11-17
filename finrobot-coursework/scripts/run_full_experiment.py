#!/usr/bin/env python3
"""
Complete A/B Experiment: FinRobot Agent vs RAG Baseline

Runs comprehensive comparison across multiple stocks, collecting:
- Latency (response time)
- Token usage (cost proxy)
- Reasoning depth (tool calls, steps)
- Response quality (length, specificity)
"""

import json
import os
import sys
import time
from datetime import datetime
from textwrap import dedent

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import autogen
from autogen import AssistantAgent, UserProxyAgent, register_function

# Data sources
import yfinance as yf

# Configuration
OAI_CONFIG = "OAI_CONFIG_LIST"
MODEL = "llama-3.3-70b-versatile"
TEMPERATURE = 0.2
OUTPUT_DIR = "results"

# Stocks to test (diverse sectors)
TICKERS = [
    "AAPL",  # Tech - Large Cap
    "MSFT",  # Tech - Large Cap
    "TSLA",  # Auto/EV - High volatility
    "JPM",   # Finance
    "JNJ",   # Healthcare
    "XOM",   # Energy
    "WMT",   # Retail
    "NVDA",  # Semiconductors
]


def get_current_date():
    return datetime.now().strftime("%Y-%m-%d")


def fetch_stock_data(ticker: str) -> dict:
    """Fetch comprehensive stock data using yfinance."""
    try:
        stock = yf.Ticker(ticker)

        # Get historical data (last 30 days)
        hist = stock.history(period="1mo")

        # Get info
        info = stock.info

        # Format for context
        data = {
            "ticker": ticker,
            "company_name": info.get("longName", ticker),
            "sector": info.get("sector", "Unknown"),
            "industry": info.get("industry", "Unknown"),
            "current_price": info.get("currentPrice", info.get("regularMarketPrice", 0)),
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("trailingPE", 0),
            "52_week_high": info.get("fiftyTwoWeekHigh", 0),
            "52_week_low": info.get("fiftyTwoWeekLow", 0),
            "avg_volume": info.get("averageVolume", 0),
            "recent_prices": {str(k): v for k, v in hist["Close"].tail(10).to_dict().items()} if not hist.empty else {},
            "price_change_1mo": ((hist["Close"].iloc[-1] / hist["Close"].iloc[0]) - 1) * 100 if len(hist) > 1 else 0,
            "volatility": hist["Close"].pct_change().std() * 100 if len(hist) > 1 else 0,
        }

        return data
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


def run_rag_experiment(ticker: str, task: str) -> dict:
    """
    RAG Baseline: Fetch all data upfront, single LLM call.
    No tool usage, no iterative reasoning.
    """
    print(f"  [RAG] Starting for {ticker}...")
    start_time = time.time()

    # Phase 1: Data retrieval (counted in total time)
    fetch_start = time.time()
    stock_data = fetch_stock_data(ticker)
    fetch_time = time.time() - fetch_start

    # Phase 2: Format context
    context = f"""
Stock Data for {ticker}:
- Company: {stock_data.get('company_name', ticker)}
- Sector: {stock_data.get('sector', 'Unknown')}
- Industry: {stock_data.get('industry', 'Unknown')}
- Current Price: ${stock_data.get('current_price', 0):.2f}
- Market Cap: ${stock_data.get('market_cap', 0):,}
- P/E Ratio: {stock_data.get('pe_ratio', 0):.2f}
- 52-Week High: ${stock_data.get('52_week_high', 0):.2f}
- 52-Week Low: ${stock_data.get('52_week_low', 0):.2f}
- 1-Month Price Change: {stock_data.get('price_change_1mo', 0):.2f}%
- Volatility (30d): {stock_data.get('volatility', 0):.2f}%
- Recent Closing Prices: {json.dumps(stock_data.get('recent_prices', {}), indent=2)}
"""

    # Phase 3: Single LLM call
    config_list = autogen.config_list_from_json(OAI_CONFIG, filter_dict={"model": [MODEL]})
    client = autogen.OpenAIWrapper(config_list=config_list)

    if task == "prediction":
        prompt = f"""
You are a financial analyst. Analyze the following stock data and provide:
1. 2-3 key positive factors (cite specific numbers from the data)
2. 2-3 risk factors or concerns (with specific numbers)
3. A 1-week price prediction with percentage change and clear reasoning

{context}

Be specific and data-driven in your analysis.
"""
    elif task == "risk_analysis":
        prompt = f"""
You are a risk analyst. Based on the following stock data:
1. Identify the top 3 risk factors (volatility, valuation, sector risks)
2. Provide specific metrics to support each risk
3. Suggest risk mitigation strategies

{context}

Use specific numbers from the data.
"""
    else:  # opportunity
        prompt = f"""
You are an investment analyst. Based on the following stock data:
1. Identify 2-3 investment opportunities
2. Support each with specific data points
3. Provide entry/exit recommendations

{context}

Be specific and actionable.
"""

    llm_start = time.time()
    response = client.create(
        messages=[{"role": "user", "content": prompt}],
        temperature=TEMPERATURE,
    )
    llm_time = time.time() - llm_start

    output = response.choices[0].message.content
    total_time = time.time() - start_time

    # Extract metrics
    result = {
        "system": "rag",
        "ticker": ticker,
        "task": task,
        "model": MODEL,
        "response": output,
        "latency_total": round(total_time, 3),
        "latency_fetch": round(fetch_time, 3),
        "latency_llm": round(llm_time, 3),
        "tool_calls": 0,  # RAG doesn't use tools
        "reasoning_steps": 1,  # Single LLM call
        "response_length": len(output),
        "prompt_tokens": len(prompt.split()),
        "completion_tokens": len(output.split()),
        "timestamp": get_current_date(),
    }

    print(f"  [RAG] {ticker} completed in {total_time:.2f}s")
    return result


def run_agent_experiment(ticker: str, task: str) -> dict:
    """
    FinRobot Agent: Uses tools iteratively, multi-step reasoning.
    """
    print(f"  [AGENT] Starting for {ticker}...")
    start_time = time.time()

    config_list = autogen.config_list_from_json(OAI_CONFIG, filter_dict={"model": [MODEL]})
    llm_config = {"config_list": config_list, "timeout": 120, "temperature": TEMPERATURE}

    # Create assistant agent
    assistant = AssistantAgent(
        "Market_Analyst",
        system_message=dedent("""
            You are a Market Analyst with access to financial tools.
            Use the provided tools to gather comprehensive data about stocks.
            Analyze the data systematically and provide specific, data-driven insights.
            Always cite specific numbers from your analysis.
            Reply TERMINATE when your analysis is complete.
        """),
        llm_config=llm_config,
    )

    # Create user proxy
    user_proxy = UserProxyAgent(
        "User_Proxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=10,
        is_termination_msg=lambda x: x.get("content", "") and "TERMINATE" in x.get("content", ""),
        code_execution_config=False,
    )

    # Track tool usage
    tool_calls = []

    def get_stock_info(symbol: str) -> str:
        """Get comprehensive stock information including price, fundamentals, and recent performance."""
        tool_calls.append(("get_stock_info", symbol))
        data = fetch_stock_data(symbol)
        return json.dumps(data, indent=2, default=str)

    def get_price_history(symbol: str, period: str = "1mo") -> str:
        """Get historical price data for a stock. Period can be: 1d, 5d, 1mo, 3mo, 6mo, 1y."""
        tool_calls.append(("get_price_history", symbol))
        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period=period)
            return hist.tail(20).to_string()
        except Exception as e:
            return f"Error: {str(e)}"

    def calculate_technicals(symbol: str) -> str:
        """Calculate technical indicators: SMA, RSI, volatility."""
        tool_calls.append(("calculate_technicals", symbol))
        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period="3mo")

            # Simple Moving Averages
            sma_20 = hist["Close"].tail(20).mean()
            sma_50 = hist["Close"].tail(50).mean()

            # Volatility
            volatility = hist["Close"].pct_change().std() * 100

            # Simple RSI approximation
            delta = hist["Close"].diff()
            gain = (delta.where(delta > 0, 0)).tail(14).mean()
            loss = (-delta.where(delta < 0, 0)).tail(14).mean()
            rs = gain / loss if loss != 0 else 0
            rsi = 100 - (100 / (1 + rs))

            current = hist["Close"].iloc[-1]

            return json.dumps({
                "current_price": round(current, 2),
                "sma_20": round(sma_20, 2),
                "sma_50": round(sma_50, 2),
                "price_vs_sma20": f"{((current/sma_20)-1)*100:.2f}%",
                "price_vs_sma50": f"{((current/sma_50)-1)*100:.2f}%",
                "rsi_14": round(rsi, 2),
                "volatility_3mo": f"{volatility:.2f}%"
            }, indent=2)
        except Exception as e:
            return f"Error: {str(e)}"

    # Register tools
    register_function(get_stock_info, caller=assistant, executor=user_proxy,
                     name="get_stock_info",
                     description="Get comprehensive stock information including price, fundamentals, and recent performance.")

    register_function(get_price_history, caller=assistant, executor=user_proxy,
                     name="get_price_history",
                     description="Get historical price data. Period: 1d, 5d, 1mo, 3mo, 6mo, 1y")

    register_function(calculate_technicals, caller=assistant, executor=user_proxy,
                     name="calculate_technicals",
                     description="Calculate technical indicators: SMA, RSI, volatility")

    # Create task prompt
    if task == "prediction":
        task_prompt = f"""
Analyze {ticker} stock and provide a comprehensive analysis:
1. Use the tools to gather stock information, price history, and technical indicators
2. Identify 2-3 key positive factors (cite specific numbers)
3. Identify 2-3 risk factors (cite specific numbers)
4. Make a 1-week price prediction with percentage change and reasoning

Use multiple tools to gather comprehensive data before making your prediction.
Reply TERMINATE when done.
"""
    elif task == "risk_analysis":
        task_prompt = f"""
Perform a risk analysis on {ticker}:
1. Use tools to gather fundamental and technical data
2. Identify top 3 risk factors with specific metrics
3. Assess volatility and valuation risks
4. Suggest risk mitigation strategies

Be thorough and use multiple data sources. Reply TERMINATE when done.
"""
    else:  # opportunity
        task_prompt = f"""
Identify investment opportunities in {ticker}:
1. Use tools to gather comprehensive data
2. Identify 2-3 specific opportunities
3. Support each with data points
4. Provide actionable recommendations

Use all available tools. Reply TERMINATE when done.
"""

    # Run conversation
    from io import StringIO
    import contextlib

    buffer = StringIO()
    with contextlib.redirect_stdout(buffer):
        user_proxy.initiate_chat(assistant, message=task_prompt, cache=None)

    total_time = time.time() - start_time
    transcript = buffer.getvalue()

    # Extract final response (last assistant message)
    final_response = ""
    if hasattr(assistant, "chat_messages") and user_proxy.name in assistant.chat_messages:
        messages = assistant.chat_messages[user_proxy.name]
        for msg in reversed(messages):
            if msg.get("role") == "assistant" and msg.get("content"):
                final_response = msg["content"]
                break

    if not final_response:
        final_response = transcript.split("Market_Analyst")[-1] if "Market_Analyst" in transcript else transcript

    # Count reasoning steps from transcript
    reasoning_steps = transcript.count("Market_Analyst") + transcript.count("User_Proxy")

    result = {
        "system": "agent",
        "ticker": ticker,
        "task": task,
        "model": MODEL,
        "response": final_response,
        "full_transcript": transcript,
        "latency_total": round(total_time, 3),
        "tool_calls": len(tool_calls),
        "tool_calls_detail": tool_calls,
        "reasoning_steps": reasoning_steps,
        "response_length": len(final_response),
        "prompt_tokens": len(task_prompt.split()) * (reasoning_steps + 1),  # Estimate
        "completion_tokens": len(final_response.split()),
        "timestamp": get_current_date(),
    }

    print(f"  [AGENT] {ticker} completed in {total_time:.2f}s ({len(tool_calls)} tools, {reasoning_steps} steps)")
    return result


def run_full_experiment():
    """Run complete A/B experiment across all stocks and tasks."""

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    tasks = ["prediction", "risk_analysis", "opportunity"]

    all_results = []
    rag_results = []
    agent_results = []

    total_experiments = len(TICKERS) * len(tasks) * 2  # RAG + Agent
    current = 0

    print(f"\n{'='*70}")
    print(f"FINROBOT vs RAG EXPERIMENT")
    print(f"Stocks: {', '.join(TICKERS)}")
    print(f"Tasks: {', '.join(tasks)}")
    print(f"Total experiments: {total_experiments}")
    print(f"{'='*70}\n")

    for ticker in TICKERS:
        print(f"\n[{ticker}] Starting experiments...")

        for task in tasks:
            current += 2
            print(f"\n  Task: {task} ({current}/{total_experiments})")

            # Run RAG baseline
            try:
                rag_result = run_rag_experiment(ticker, task)
                rag_results.append(rag_result)
                all_results.append(rag_result)
            except Exception as e:
                print(f"  [RAG] ERROR: {e}")
                rag_results.append({"system": "rag", "ticker": ticker, "task": task, "error": str(e)})

            # Small delay to avoid rate limits
            time.sleep(2)

            # Run Agent
            try:
                agent_result = run_agent_experiment(ticker, task)
                agent_results.append(agent_result)
                all_results.append(agent_result)
            except Exception as e:
                print(f"  [AGENT] ERROR: {e}")
                agent_results.append({"system": "agent", "ticker": ticker, "task": task, "error": str(e)})

            # Delay between experiments
            time.sleep(3)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save all results
    with open(f"{OUTPUT_DIR}/all_results_{timestamp}.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    # Save RAG results
    with open(f"{OUTPUT_DIR}/rag_results_{timestamp}.json", "w") as f:
        json.dump(rag_results, f, indent=2, default=str)

    # Save Agent results
    with open(f"{OUTPUT_DIR}/agent_results_{timestamp}.json", "w") as f:
        json.dump(agent_results, f, indent=2, default=str)

    # Create summary CSV
    import csv
    with open(f"{OUTPUT_DIR}/summary_{timestamp}.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "system", "ticker", "task", "latency_total", "tool_calls",
            "reasoning_steps", "response_length", "prompt_tokens", "completion_tokens"
        ])

        for result in all_results:
            if "error" not in result:
                writer.writerow([
                    result.get("system", ""),
                    result.get("ticker", ""),
                    result.get("task", ""),
                    result.get("latency_total", 0),
                    result.get("tool_calls", 0),
                    result.get("reasoning_steps", 0),
                    result.get("response_length", 0),
                    result.get("prompt_tokens", 0),
                    result.get("completion_tokens", 0),
                ])

    # Print summary statistics
    print(f"\n{'='*70}")
    print("EXPERIMENT SUMMARY")
    print(f"{'='*70}")

    rag_latencies = [r.get("latency_total", 0) for r in rag_results if "error" not in r]
    agent_latencies = [r.get("latency_total", 0) for r in agent_results if "error" not in r]
    agent_tools = [r.get("tool_calls", 0) for r in agent_results if "error" not in r]

    if rag_latencies and agent_latencies:
        print(f"\nRAG Baseline:")
        print(f"  Avg Latency: {sum(rag_latencies)/len(rag_latencies):.2f}s")
        print(f"  Min Latency: {min(rag_latencies):.2f}s")
        print(f"  Max Latency: {max(rag_latencies):.2f}s")
        print(f"  Tool Calls: 0 (always)")

        print(f"\nFinRobot Agent:")
        print(f"  Avg Latency: {sum(agent_latencies)/len(agent_latencies):.2f}s")
        print(f"  Min Latency: {min(agent_latencies):.2f}s")
        print(f"  Max Latency: {max(agent_latencies):.2f}s")
        print(f"  Avg Tool Calls: {sum(agent_tools)/len(agent_tools):.1f}")

        print(f"\nAgent vs RAG:")
        print(f"  Latency Ratio: {sum(agent_latencies)/len(agent_latencies) / (sum(rag_latencies)/len(rag_latencies)):.2f}x")

    print(f"\nResults saved to {OUTPUT_DIR}/")
    print(f"  - all_results_{timestamp}.json")
    print(f"  - rag_results_{timestamp}.json")
    print(f"  - agent_results_{timestamp}.json")
    print(f"  - summary_{timestamp}.csv")

    return all_results


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    results = run_full_experiment()
    print(f"\n\nExperiment complete! {len(results)} total results collected.")
