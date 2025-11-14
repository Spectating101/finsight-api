#!/usr/bin/env python3
"""
FinRobot Agent with ONLY yfinance (no Finnhub dependencies)
"""
import argparse
import json
import os
import time
from textwrap import dedent

import autogen
from finrobot.utils import get_current_date
from finrobot.data_source import YFinanceUtils
from autogen import AssistantAgent, UserProxyAgent, register_function

# Add delay between API calls to avoid queue limits
def delayed_create(*args, **kwargs):
    time.sleep(2)
    return autogen.oai.client.OpenAIWrapper._original_create(*args, **kwargs)

if not hasattr(autogen.oai.client.OpenAIWrapper, '_original_create'):
    autogen.oai.client.OpenAIWrapper._original_create = autogen.oai.client.OpenAIWrapper.create
    autogen.oai.client.OpenAIWrapper.create = delayed_create


def run_agent(ticker: str, model: str, oai_config: str, temperature: float) -> dict:
    """Run agent with yfinance tools only"""
    
    config_list = autogen.config_list_from_json(oai_config, filter_dict={"model": [model]})
    if not config_list:
        raise ValueError(f"Model {model} not found in {oai_config}")
    
    llm_config = {"config_list": config_list, "timeout": 120, "temperature": temperature}
    
    # Create assistant
    assistant = AssistantAgent(
        "Market_Analyst",
        system_message="You are a Market Analyst. Use the provided tools to analyze stocks comprehensively. Reply TERMINATE when done.",
        llm_config=llm_config,
    )
    
    # Create user proxy
    user_proxy = UserProxyAgent(
        "User_Proxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=15,
        is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").endswith("TERMINATE"),
        code_execution_config={"work_dir": "coding", "use_docker": False},
    )
    
    # Wrapper to handle save_path validation issue
    def get_stock_data_wrapper(symbol: str, start_date: str, end_date: str, save_path: str = "") -> str:
        """Retrieve stock price data for designated ticker symbol.
        Args:
            symbol: ticker symbol
            start_date: start date YYYY-MM-DD  
            end_date: end date YYYY-MM-DD
            save_path: file path to save (use empty string if not saving)
        """
        # Call with empty string instead of None
        if not save_path or save_path == "null":
            save_path = ""
        result = YFinanceUtils.get_stock_data(symbol, start_date, end_date, save_path or None)
        return str(result)
    
    # Register wrapper
    register_function(
        get_stock_data_wrapper,
        caller=assistant,
        executor=user_proxy,
        name="get_stock_data",
        description=get_stock_data_wrapper.__doc__,
    )
    
    prompt = dedent(f"""
        Analyze {ticker} stock comprehensively using the get_stock_data tool.
        
        Provide detailed analysis with SPECIFIC DATA including:
        1. Key positive developments (cite specific prices, dates, percentages)
        2. Key concerns (with numbers)
        3. 1-week price prediction with % change and reasoning
        
        Reply TERMINATE when analysis is complete.
    """).strip()
    
    start_time = time.time()
    from io import StringIO
    import contextlib
    
    buffer = StringIO()
    with contextlib.redirect_stdout(buffer):
        user_proxy.initiate_chat(assistant, message=prompt, cache=None)
    
    elapsed = time.time() - start_time
    full_transcript = buffer.getvalue()
    
    return {
        "system": "agent",
        "ticker": ticker,
        "model": model,
        "temperature": temperature,
        "transcript": full_transcript,
        "latency_seconds": round(elapsed, 2),
        "timestamp": get_current_date(),
    }


def main():
    parser = argparse.ArgumentParser(description="Run FinRobot Agent with yfinance")
    parser.add_argument("tickers", nargs="+", help="Stock tickers")
    parser.add_argument("--model", default="llama-3.3-70b", help="Model name")
    parser.add_argument("--oai-config", default="OAI_CONFIG_LIST", help="Config file")
    parser.add_argument("--temperature", type=float, default=0.2, help="Temperature")
    parser.add_argument("--output", required=True, help="Output JSON")
    
    args = parser.parse_args()
    
    results = []
    for ticker in args.tickers:
        print(f"\n{'='*60}")
        print(f"Running AGENT on {ticker}")
        print(f"{'='*60}")
        try:
            result = run_agent(ticker, args.model, args.oai_config, args.temperature)
            results.append(result)
            print(f"✓ {ticker} completed in {result['latency_seconds']}s")
        except Exception as e:
            print(f"✗ {ticker} failed: {e}")
            results.append({"system": "agent", "ticker": ticker, "error": str(e)})
    
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✓ Saved to {args.output}")


if __name__ == "__main__":
    main()

