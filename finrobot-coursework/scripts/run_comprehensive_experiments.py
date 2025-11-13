"""
Phase 4: Comprehensive Agent vs RAG Comparison Experiments

This script runs sophisticated experiments comparing:
- FinRobot Agent (multi-tool orchestration)
- RAG System (retrieval + LLM)

Across multiple dimensions:
- Performance: Latency, throughput
- Cost: API token usage
- Quality: Accuracy, reasoning depth
- Robustness: Error handling, edge cases

Generates data for statistical analysis and research paper.
"""

import json
import time
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple
import os

from finrobot.experiments.experiment_runner import FinRobotExperimentRunner, ExperimentConfig
from finrobot.experiments.rag_system import RAGChain
from finrobot.experiments.metrics_collector import MetricsCollector
from finrobot.experiments.fact_checker import FactChecker
from finrobot.logging import get_logger

logger = get_logger(__name__)

# Experiment configuration
STOCKS = [
    # Tech giants
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
    # Finance
    "JPM", "BAC", "GS",
    # Healthcare
    "JNJ", "PFE",
    # Consumer
    "WMT", "KO",
    # Energy
    "XOM", "CVX",
    # Diverse market caps and sectors for robustness
]

TASKS = [
    {
        "name": "price_prediction",
        "prompt": "Analyze {ticker}'s recent performance and predict whether the stock price will increase or decrease in the next quarter. Provide specific reasoning based on fundamentals, market trends, and recent news.",
        "category": "prediction",
        "difficulty": "hard"
    },
    {
        "name": "risk_assessment",
        "prompt": "Assess the investment risk of {ticker}. Consider financial health, market position, industry trends, and recent developments. Rate risk as LOW, MEDIUM, or HIGH with detailed justification.",
        "category": "analysis",
        "difficulty": "medium"
    },
    {
        "name": "fundamental_analysis",
        "prompt": "Provide a comprehensive fundamental analysis of {ticker}. Include key financial ratios (P/E, ROE, debt-to-equity), revenue trends, profitability, and competitive position.",
        "category": "analysis",
        "difficulty": "medium"
    },
    {
        "name": "buy_hold_sell",
        "prompt": "Based on current market conditions and {ticker}'s fundamentals, provide a BUY, HOLD, or SELL recommendation. Justify your recommendation with specific metrics and analysis.",
        "category": "recommendation",
        "difficulty": "hard"
    },
    {
        "name": "news_impact",
        "prompt": "Analyze recent news about {ticker} and assess how it might impact the stock price in the short term (1-3 months). Consider both positive and negative factors.",
        "category": "analysis",
        "difficulty": "medium"
    }
]


class ComprehensiveExperimentSuite:
    """
    Runs sophisticated experiments comparing Agent vs RAG.

    Features:
    - Multiple stocks across sectors
    - Multiple task types (prediction, analysis, recommendation)
    - Robust metrics collection
    - Statistical validation
    - Error handling and retries
    - Results export for analysis
    """

    def __init__(self, output_dir: str = "experiment_results"):
        """Initialize experiment suite."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.agent_runner = FinRobotExperimentRunner()
        self.rag_system = RAGChain()
        self.metrics_collector = MetricsCollector()
        self.fact_checker = FactChecker()

        self.results = {
            "agent": [],
            "rag": []
        }

        logger.info(f"Experiment suite initialized. Output: {self.output_dir}")

    def run_single_experiment(
        self,
        system: str,
        ticker: str,
        task: Dict[str, str],
        run_id: int
    ) -> Dict[str, Any]:
        """
        Run a single experiment.

        Args:
            system: "agent" or "rag"
            ticker: Stock ticker
            task: Task definition
            run_id: Experiment run ID

        Returns:
            Results dict with metrics
        """
        logger.info(f"Running {system} on {ticker} - {task['name']} (run {run_id})")

        prompt = task["prompt"].format(ticker=ticker)
        start_time = time.time()

        try:
            if system == "agent":
                # Run FinRobot agent
                metric_snapshot = self.agent_runner.run_agent_analysis(
                    ticker=ticker,
                    task_prompt=prompt,
                    task_name=task["name"]
                )
                response = metric_snapshot.output

            else:  # RAG
                # Run RAG system
                rag_result = self.rag_system.query(ticker, prompt)
                response = rag_result.get("answer", "")

                # Convert to metric snapshot for consistency
                metric_snapshot = self.rag_system.get_metrics()

            latency = time.time() - start_time

            # Extract key metrics
            result = {
                "run_id": run_id,
                "system": system,
                "ticker": ticker,
                "task_name": task["name"],
                "task_category": task["category"],
                "task_difficulty": task["difficulty"],
                "latency_seconds": latency,
                "response_length": len(response),
                "success": True,
                "timestamp": datetime.now().isoformat(),
            }

            # Add system-specific metrics
            if hasattr(metric_snapshot, 'total_cost_usd'):
                result["cost_usd"] = metric_snapshot.total_cost_usd
            if hasattr(metric_snapshot, 'reasoning_depth'):
                result["reasoning_depth"] = metric_snapshot.reasoning_depth
            if hasattr(metric_snapshot, 'tool_calls'):
                result["tool_calls"] = len(metric_snapshot.tool_calls) if metric_snapshot.tool_calls else 0

            # Analyze response quality
            result.update(self._analyze_response_quality(response, task))

            # Store response for qualitative analysis
            result["response"] = response[:500]  # First 500 chars for review

            logger.info(f"Completed {system} on {ticker}: {latency:.2f}s")

            return result

        except Exception as e:
            logger.error(f"Experiment failed: {system} on {ticker} - {str(e)}")
            return {
                "run_id": run_id,
                "system": system,
                "ticker": ticker,
                "task_name": task["name"],
                "task_category": task["category"],
                "task_difficulty": task["difficulty"],
                "latency_seconds": time.time() - start_time,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def _analyze_response_quality(self, response: str, task: Dict[str, str]) -> Dict[str, Any]:
        """
        Analyze response quality metrics.

        Args:
            response: System response
            task: Task definition

        Returns:
            Quality metrics dict
        """
        quality = {}

        # Length-based metrics
        quality["word_count"] = len(response.split())
        quality["sentence_count"] = len([s for s in response.split('.') if s.strip()])

        # Check for key elements based on task type
        if task["category"] == "prediction":
            quality["has_prediction"] = any(word in response.lower() for word in ["increase", "decrease", "rise", "fall", "up", "down"])
            quality["has_reasoning"] = any(word in response.lower() for word in ["because", "since", "due to", "based on"])

        elif task["category"] == "recommendation":
            quality["has_recommendation"] = any(word in response.upper() for word in ["BUY", "SELL", "HOLD"])
            quality["has_justification"] = len(response.split()) > 50

        elif task["category"] == "analysis":
            quality["has_numbers"] = bool(re.search(r'\d+\.?\d*', response))
            quality["has_analysis_keywords"] = any(word in response.lower() for word in ["ratio", "metric", "financial", "performance"])

        # Sentiment and confidence
        quality["confident_language"] = any(word in response.lower() for word in ["strong", "significant", "clear", "definitely", "certainly"])
        quality["hedging_language"] = any(word in response.lower() for word in ["may", "might", "possibly", "potentially", "could"])

        return quality

    def run_full_comparison(
        self,
        num_stocks: int = 10,
        num_tasks: int = 3,
        runs_per_experiment: int = 1
    ):
        """
        Run comprehensive comparison experiments.

        Args:
            num_stocks: Number of stocks to test
            num_tasks: Number of tasks per stock
            runs_per_experiment: Runs for reliability
        """
        logger.info(f"Starting full comparison: {num_stocks} stocks, {num_tasks} tasks, {runs_per_experiment} runs each")

        selected_stocks = STOCKS[:num_stocks]
        selected_tasks = TASKS[:num_tasks]

        total_experiments = num_stocks * num_tasks * 2 * runs_per_experiment  # 2 systems
        completed = 0

        for run_id in range(runs_per_experiment):
            for ticker in selected_stocks:
                for task in selected_tasks:
                    # Run agent
                    agent_result = self.run_single_experiment("agent", ticker, task, run_id)
                    self.results["agent"].append(agent_result)
                    completed += 1
                    logger.info(f"Progress: {completed}/{total_experiments} ({completed/total_experiments*100:.1f}%)")

                    # Run RAG
                    rag_result = self.run_single_experiment("rag", ticker, task, run_id)
                    self.results["rag"].append(rag_result)
                    completed += 1
                    logger.info(f"Progress: {completed}/{total_experiments} ({completed/total_experiments*100:.1f}%)")

        logger.info("All experiments completed!")
        self._save_results()
        self._generate_summary()

    def _save_results(self):
        """Save raw results to JSON and CSV."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save JSON (full data)
        json_path = self.output_dir / f"results_{timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"Results saved to {json_path}")

        # Save CSV (for easy analysis)
        agent_df = pd.DataFrame(self.results["agent"])
        rag_df = pd.DataFrame(self.results["rag"])
        combined_df = pd.concat([agent_df, rag_df], ignore_index=True)

        csv_path = self.output_dir / f"results_{timestamp}.csv"
        combined_df.to_csv(csv_path, index=False)
        logger.info(f"CSV saved to {csv_path}")

        return json_path, csv_path

    def _generate_summary(self):
        """Generate statistical summary."""
        agent_df = pd.DataFrame([r for r in self.results["agent"] if r.get("success")])
        rag_df = pd.DataFrame([r for r in self.results["rag"] if r.get("success")])

        summary = {
            "experiment_date": datetime.now().isoformat(),
            "total_experiments": len(self.results["agent"]) + len(self.results["rag"]),
            "agent": self._compute_system_stats(agent_df),
            "rag": self._compute_system_stats(rag_df),
        }

        # Save summary
        summary_path = self.output_dir / "summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)

        logger.info(f"Summary saved to {summary_path}")
        self._print_summary(summary)

        return summary

    def _compute_system_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Compute statistics for a system."""
        if df.empty:
            return {"error": "No successful experiments"}

        stats = {
            "total_runs": len(df),
            "success_rate": (df["success"].sum() / len(df)) if "success" in df else 1.0,
            "latency": {
                "mean": df["latency_seconds"].mean(),
                "std": df["latency_seconds"].std(),
                "min": df["latency_seconds"].min(),
                "max": df["latency_seconds"].max(),
                "median": df["latency_seconds"].median(),
            },
            "response_length": {
                "mean": df["response_length"].mean(),
                "std": df["response_length"].std(),
            },
        }

        if "cost_usd" in df.columns:
            stats["cost"] = {
                "total": df["cost_usd"].sum(),
                "mean": df["cost_usd"].mean(),
                "std": df["cost_usd"].std(),
            }

        if "tool_calls" in df.columns:
            stats["tool_calls"] = {
                "mean": df["tool_calls"].mean(),
                "std": df["tool_calls"].std(),
            }

        return stats

    def _print_summary(self, summary: Dict[str, Any]):
        """Print summary to console."""
        print("\n" + "="*80)
        print("EXPERIMENT SUMMARY")
        print("="*80)

        for system in ["agent", "rag"]:
            if system not in summary:
                continue

            print(f"\n{system.upper()} System:")
            stats = summary[system]

            if "error" in stats:
                print(f"  ❌ {stats['error']}")
                continue

            print(f"  Total Runs: {stats['total_runs']}")
            print(f"  Success Rate: {stats['success_rate']:.1%}")
            print(f"  Latency: {stats['latency']['mean']:.2f}s (±{stats['latency']['std']:.2f}s)")
            print(f"  Response Length: {stats['response_length']['mean']:.0f} chars")

            if "cost" in stats:
                print(f"  Total Cost: ${stats['cost']['total']:.4f}")
                print(f"  Avg Cost: ${stats['cost']['mean']:.4f}")

            if "tool_calls" in stats:
                print(f"  Avg Tool Calls: {stats['tool_calls']['mean']:.1f}")

        print("\n" + "="*80)


def main():
    """Run comprehensive experiments."""
    import argparse

    parser = argparse.ArgumentParser(description="Run Agent vs RAG comparison experiments")
    parser.add_argument("--stocks", type=int, default=10, help="Number of stocks to test")
    parser.add_argument("--tasks", type=int, default=3, help="Number of tasks per stock")
    parser.add_argument("--runs", type=int, default=1, help="Number of runs for reliability")
    parser.add_argument("--output", type=str, default="experiment_results", help="Output directory")

    args = parser.parse_args()

    # Create and run experiment suite
    suite = ComprehensiveExperimentSuite(output_dir=args.output)
    suite.run_full_comparison(
        num_stocks=args.stocks,
        num_tasks=args.tasks,
        runs_per_experiment=args.runs
    )

    print("\n✅ Experiments complete! Results saved to:", args.output)
    print("Next step: Run analysis with scripts/analyze_results.py")


if __name__ == "__main__":
    main()
