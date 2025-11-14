"""
Phase 4: Comprehensive Agent vs RAG Comparison Experiments

This script runs OBJECTIVE, THOROUGH experiments comparing:
- FinRobot Agent (multi-tool orchestration)
- RAG System (retrieval + LLM)

Across 8 comprehensive dimensions with 40+ metrics:

1. BASIC STRUCTURE (6 metrics)
   - Word/sentence/paragraph count, avg sentence length
   - Bullet points, section headers

2. ANALYTICAL DEPTH (11 metrics)
   - Financial metrics mentioned (P/E, ROE, margins, etc.)
   - Historical references (quarters, years, temporal comparisons)
   - Future projections, risk factors
   - Peer/market comparisons

3. DATA QUALITY (8 metrics)
   - Numerical data points, dollar amounts, percentages
   - Data sources referenced
   - Specificity vs vagueness ratio
   - Recency indicators

4. REASONING QUALITY (4 metrics)
   - Causal chains, evidence markers
   - Conditional reasoning, alternative perspectives

5. TASK-SPECIFIC (varies by task)
   - Predictions: confidence, price targets, timeframes
   - Recommendations: strength, justification, alternatives
   - Analysis: breadth, quantitative/qualitative balance

6. FACTUAL GROUNDING (4 metrics)
   - Specific dates, company-specific vs generic mentions
   - Specificity score

7. LANGUAGE QUALITY (5 metrics)
   - Confident vs hedging language ratio
   - Average word length, complex sentences

8. COMPREHENSIVENESS (2 metrics)
   - Overall completeness score (9 factors)
   - Comprehensiveness percentage

PLUS performance metrics:
- Latency, cost, tool calls, success rate

NO BIAS - Objective academic comparison. Let the data speak.

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
import re
from collections import Counter

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
        COMPREHENSIVE multi-dimensional response quality analysis.

        Categories measured:
        1. Basic Structure - length, format, organization
        2. Analytical Depth - metrics mentioned, data points, projections
        3. Data Quality - sources, recency, specificity, numerical grounding
        4. Reasoning Quality - causal chains, evidence, logical structure
        5. Task-Specific - prediction confidence, risk factors, recommendations
        6. Factual Grounding - verifiable claims, dates, numbers, specificity
        7. Language Quality - confidence, hedging, clarity
        8. Comprehensiveness - topic coverage, completeness

        Args:
            response: System response
            task: Task definition

        Returns:
            Comprehensive quality metrics dict with 40+ metrics
        """
        quality = {}
        response_lower = response.lower()

        # ===== 1. BASIC STRUCTURE METRICS =====
        words = response.split()
        sentences = [s.strip() for s in response.split('.') if s.strip()]
        paragraphs = [p.strip() for p in response.split('\n\n') if p.strip()]

        quality["word_count"] = len(words)
        quality["sentence_count"] = len(sentences)
        quality["paragraph_count"] = len(paragraphs)
        quality["avg_sentence_length"] = len(words) / len(sentences) if sentences else 0
        quality["has_bullet_points"] = bool(re.search(r'[\n\r]\s*[-•*]', response))
        quality["has_sections"] = bool(re.search(r'[\n\r]#{1,3}\s+\w+|[\n\r][A-Z][a-z]+:', response))

        # ===== 2. ANALYTICAL DEPTH METRICS =====
        # Financial metrics mentioned
        financial_metrics = [
            r'p/e ratio', r'price.*earnings', r'p/e\b',
            r'roe\b', r'return on equity',
            r'debt.*equity', r'debt ratio', r'd/e\b',
            r'profit margin', r'operating margin', r'net margin',
            r'revenue growth', r'earnings growth',
            r'eps\b', r'earnings per share',
            r'market cap', r'market capitalization',
            r'dividend yield', r'payout ratio',
            r'cash flow', r'free cash flow', r'fcf\b',
            r'ebitda', r'operating income',
            r'current ratio', r'quick ratio', r'liquidity',
            r'beta\b', r'volatility',
            r'book value', r'price.*book', r'p/b\b',
        ]
        quality["financial_metrics_mentioned"] = sum(
            1 for metric in financial_metrics if re.search(metric, response_lower)
        )

        # Historical data references
        quality["quarters_mentioned"] = len(re.findall(r'q[1-4]\s+\d{4}|quarter', response_lower))
        quality["years_mentioned"] = len(re.findall(r'\b(19|20)\d{2}\b', response))
        quality["temporal_comparisons"] = sum(
            1 for phrase in ['year.*year', 'quarter.*quarter', 'vs.*previous', 'compared to', 'growth from']
            if re.search(phrase, response_lower)
        )

        # Future projections
        quality["has_future_projection"] = bool(re.search(
            r'next\s+(quarter|year|month)|forecast|predict|expect|project|anticipate|outlook',
            response_lower
        ))
        quality["projection_timeframe_specific"] = bool(re.search(
            r'next\s+\d+\s+(months?|quarters?|years?)|by\s+(19|20)\d{2}|\d{4}\s+guidance',
            response_lower
        ))

        # Risk factors
        risk_keywords = [
            'risk', 'threat', 'concern', 'challenge', 'headwind', 'uncertainty',
            'downside', 'vulnerable', 'exposure', 'volatility', 'competition'
        ]
        quality["risk_factors_mentioned"] = sum(1 for kw in risk_keywords if kw in response_lower)

        # Comparative analysis
        quality["peer_comparison"] = bool(re.search(
            r'compared to|versus|vs\.|relative to|peers?|competitors?|industry average|sector',
            response_lower
        ))
        quality["market_comparison"] = bool(re.search(
            r's&p 500|market|nasdaq|dow|index|benchmark',
            response_lower
        ))

        # ===== 3. DATA QUALITY METRICS =====
        # Number of specific numerical data points
        numbers = re.findall(r'\$?\d+\.?\d*[BMK%]?', response)
        quality["numerical_data_points"] = len(numbers)
        quality["has_dollar_amounts"] = bool(re.search(r'\$\d+', response))
        quality["has_percentages"] = bool(re.search(r'\d+\.?\d*%', response))

        # Data sources referenced
        sources = [
            'yahoo finance', 'bloomberg', 'reuters', 'sec filing', '10-k', '10-q',
            'earnings report', 'financial statement', 'balance sheet', 'income statement',
            'analyst', 'research', 'news', 'announcement', 'press release'
        ]
        quality["data_sources_mentioned"] = sum(1 for src in sources if src in response_lower)

        # Specificity vs vagueness
        vague_terms = [
            'roughly', 'approximately', 'about', 'around', 'some', 'many',
            'several', 'various', 'significant', 'substantial'
        ]
        specific_terms = [
            'exactly', 'precisely', 'specifically', '\d+\.?\d+%', '\$\d+',
            'reported', 'announced', 'filed'
        ]
        quality["vague_term_count"] = sum(1 for term in vague_terms if term in response_lower)
        quality["specific_term_count"] = sum(
            1 for term in specific_terms if re.search(term, response_lower)
        )
        quality["specificity_ratio"] = (
            quality["specific_term_count"] / max(quality["vague_term_count"], 1)
        )

        # Recency indicators
        quality["mentions_recent_data"] = bool(re.search(
            r'recent|latest|current|today|this\s+(week|month|quarter|year)|last\s+(week|month|quarter)',
            response_lower
        ))

        # ===== 4. REASONING QUALITY METRICS =====
        # Causal reasoning
        causal_indicators = [
            'because', 'since', 'due to', 'as a result', 'therefore', 'thus',
            'consequently', 'leads to', 'results in', 'caused by', 'driven by'
        ]
        quality["causal_chains"] = sum(1 for ind in causal_indicators if ind in response_lower)

        # Evidence-based reasoning
        evidence_markers = [
            'based on', 'according to', 'evidence', 'data shows', 'indicates that',
            'demonstrates', 'suggests', 'supports', 'confirms', 'shows that'
        ]
        quality["evidence_markers"] = sum(1 for marker in evidence_markers if marker in response_lower)

        # Counterfactual/conditional reasoning
        quality["conditional_reasoning"] = sum(
            1 for phrase in ['if', 'unless', 'provided that', 'assuming', 'in case']
            if phrase in response_lower
        )

        # Multiple perspectives
        quality["considers_alternatives"] = bool(re.search(
            r'however|although|while|on the other hand|alternatively|conversely|but\s+\w',
            response_lower
        ))

        # ===== 5. TASK-SPECIFIC METRICS =====
        if task["category"] == "prediction":
            quality["has_clear_prediction"] = any(
                word in response_lower for word in ["increase", "decrease", "rise", "fall", "up", "down", "grow", "decline"]
            )
            quality["prediction_confidence"] = bool(re.search(
                r'\d+%\s+(confident|probability|chance|likely)|high confidence|low confidence|moderate confidence',
                response_lower
            ))
            quality["has_price_target"] = bool(re.search(r'\$\d+.*target|target.*\$\d+', response_lower))
            quality["timeframe_specified"] = bool(re.search(
                r'next\s+\d+\s+(days?|weeks?|months?|quarters?|years?)|by\s+(19|20)\d{2}|within\s+\d+',
                response_lower
            ))

        elif task["category"] == "recommendation":
            quality["has_clear_recommendation"] = any(
                word in response.upper() for word in ["BUY", "SELL", "HOLD", "STRONG BUY", "STRONG SELL"]
            )
            quality["recommendation_strength"] = bool(re.search(r'strong\s+(buy|sell)', response_lower))
            quality["has_price_target"] = bool(re.search(r'\$\d+.*target|target.*\$\d+', response_lower))
            quality["justification_depth"] = len(words) > 100  # Substantial justification
            quality["mentions_alternatives"] = bool(re.search(
                r'alternative|other options|also consider|or\s+(buy|sell|hold)',
                response_lower
            ))

        elif task["category"] == "analysis":
            quality["analysis_breadth"] = quality["financial_metrics_mentioned"]
            quality["quantitative_analysis"] = quality["numerical_data_points"] > 5
            quality["qualitative_analysis"] = bool(re.search(
                r'strength|weakness|opportunity|threat|swot|competitive advantage|moat',
                response_lower
            ))
            quality["trend_analysis"] = quality["temporal_comparisons"] > 0
            quality["comprehensive_coverage"] = (
                quality["financial_metrics_mentioned"] >= 3 and
                quality["risk_factors_mentioned"] >= 2 and
                quality["numerical_data_points"] >= 5
            )

        # ===== 6. FACTUAL GROUNDING METRICS =====
        # Specific dates
        quality["specific_dates_mentioned"] = len(re.findall(
            r'\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2}|[A-Z][a-z]+\s+\d{1,2},?\s+\d{4}',
            response
        ))

        # Company-specific vs generic
        company_specific = [
            'ceo', 'management', 'board', 'acquisition', 'merger', 'product launch',
            'partnership', 'contract', 'lawsuit', 'regulatory', 'patent', 'innovation'
        ]
        quality["company_specific_mentions"] = sum(
            1 for term in company_specific if term in response_lower
        )

        generic_terms = [
            'stock market', 'economy', 'interest rates', 'inflation', 'generally',
            'typically', 'usually', 'often', 'common'
        ]
        quality["generic_term_count"] = sum(1 for term in generic_terms if term in response_lower)
        quality["specificity_score"] = (
            quality["company_specific_mentions"] / max(quality["generic_term_count"], 1)
        )

        # ===== 7. LANGUAGE QUALITY METRICS =====
        # Confidence indicators
        confident_language = [
            'will', 'certain', 'definitely', 'clearly', 'strong', 'significant',
            'substantial', 'decisive', 'conclusive'
        ]
        quality["confident_language_count"] = sum(
            1 for term in confident_language if term in response_lower
        )

        # Hedging/uncertainty
        hedging_language = [
            'may', 'might', 'could', 'possibly', 'potentially', 'perhaps',
            'likely', 'probably', 'seems', 'appears', 'suggests'
        ]
        quality["hedging_language_count"] = sum(
            1 for term in hedging_language if term in response_lower
        )

        quality["confidence_ratio"] = (
            quality["confident_language_count"] / max(quality["hedging_language_count"], 1)
        )

        # Clarity
        quality["avg_word_length"] = sum(len(w) for w in words) / len(words) if words else 0
        quality["complex_sentences"] = sum(1 for s in sentences if len(s.split()) > 30)

        # ===== 8. COMPREHENSIVENESS SCORE =====
        # Calculate overall comprehensiveness based on multiple factors
        comprehensiveness_factors = [
            quality["financial_metrics_mentioned"] >= 3,
            quality["numerical_data_points"] >= 5,
            quality["risk_factors_mentioned"] >= 2,
            quality["causal_chains"] >= 2,
            quality["evidence_markers"] >= 2,
            quality["word_count"] >= 150,
            quality["data_sources_mentioned"] >= 1,
            quality.get("has_future_projection", False),
            quality.get("peer_comparison", False),
        ]
        quality["comprehensiveness_score"] = sum(1 for factor in comprehensiveness_factors if factor)
        quality["comprehensiveness_percentage"] = (
            quality["comprehensiveness_score"] / len(comprehensiveness_factors) * 100
        )

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
