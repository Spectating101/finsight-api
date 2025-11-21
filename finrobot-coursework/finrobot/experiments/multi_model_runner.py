"""
Multi-model experiment runner for comprehensive evaluation.

Supports running experiments across multiple LLM models to demonstrate
that results are not model-specific. Addresses the "single model only" criticism.

Supported models:
- OpenAI: GPT-4, GPT-4-Turbo, GPT-3.5-Turbo
- Anthropic: Claude-3.5-Sonnet, Claude-3-Opus, Claude-3-Haiku
- Open source: LLaMA-3.3-70B (via inference endpoints)
- Google: Gemini-Pro (via API)
"""

import time
import json
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum

from finrobot.logging import get_logger
from finrobot.experiments.metrics_collector import MetricsCollector, MetricSnapshot
from finrobot.experiments.fact_checker import FactChecker
from finrobot.experiments.ground_truth_validator import (
    GroundTruthValidator,
    PredictionType,
)
from finrobot.experiments.statistical_analysis import StatisticalAnalyzer

logger = get_logger(__name__)


class ModelProvider(Enum):
    """Supported model providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    TOGETHER = "together"  # For LLaMA
    GOOGLE = "google"  # For Gemini


@dataclass
class ModelConfig:
    """Configuration for a specific model."""

    name: str  # Display name
    provider: ModelProvider
    model_id: str  # API model identifier
    max_tokens: int = 4096
    temperature: float = 0.2
    supports_function_calling: bool = True
    cost_per_1k_prompt: float = 0.0
    cost_per_1k_completion: float = 0.0

    @classmethod
    def gpt4(cls) -> "ModelConfig":
        """GPT-4 configuration."""
        return cls(
            name="GPT-4",
            provider=ModelProvider.OPENAI,
            model_id="gpt-4",
            cost_per_1k_prompt=0.03,
            cost_per_1k_completion=0.06,
        )

    @classmethod
    def gpt4_turbo(cls) -> "ModelConfig":
        """GPT-4-Turbo configuration."""
        return cls(
            name="GPT-4-Turbo",
            provider=ModelProvider.OPENAI,
            model_id="gpt-4-turbo-preview",
            cost_per_1k_prompt=0.01,
            cost_per_1k_completion=0.03,
        )

    @classmethod
    def gpt35(cls) -> "ModelConfig":
        """GPT-3.5-Turbo configuration."""
        return cls(
            name="GPT-3.5-Turbo",
            provider=ModelProvider.OPENAI,
            model_id="gpt-3.5-turbo",
            cost_per_1k_prompt=0.0005,
            cost_per_1k_completion=0.0015,
        )

    @classmethod
    def claude_35_sonnet(cls) -> "ModelConfig":
        """Claude-3.5-Sonnet configuration."""
        return cls(
            name="Claude-3.5-Sonnet",
            provider=ModelProvider.ANTHROPIC,
            model_id="claude-3-5-sonnet-20241022",
            cost_per_1k_prompt=0.003,
            cost_per_1k_completion=0.015,
        )

    @classmethod
    def claude_opus(cls) -> "ModelConfig":
        """Claude-3-Opus configuration."""
        return cls(
            name="Claude-3-Opus",
            provider=ModelProvider.ANTHROPIC,
            model_id="claude-3-opus-20240229",
            cost_per_1k_prompt=0.015,
            cost_per_1k_completion=0.075,
        )

    @classmethod
    def llama_70b(cls) -> "ModelConfig":
        """LLaMA-3.3-70B configuration."""
        return cls(
            name="LLaMA-3.3-70B",
            provider=ModelProvider.TOGETHER,
            model_id="meta-llama/Llama-3.3-70B-Instruct-Turbo",
            cost_per_1k_prompt=0.0009,
            cost_per_1k_completion=0.0009,
        )

    @classmethod
    def gemini_pro(cls) -> "ModelConfig":
        """Gemini-Pro configuration."""
        return cls(
            name="Gemini-Pro",
            provider=ModelProvider.GOOGLE,
            model_id="gemini-pro",
            cost_per_1k_prompt=0.00025,
            cost_per_1k_completion=0.0005,
        )


@dataclass
class ExperimentPlan:
    """Comprehensive experiment plan."""

    # Systems to test
    systems: List[str]  # ["agent", "rag", "zeroshot"]

    # Models to test
    models: List[ModelConfig]

    # Stocks to test
    tickers: List[str]

    # Tasks per stock
    tasks: List[Dict[str, str]]  # [{"name": str, "prompt": str}]

    # Validation settings
    enable_ground_truth_validation: bool = True
    prediction_timeframe_days: int = 7

    # Statistical settings
    run_statistical_analysis: bool = True
    confidence_level: float = 0.95

    def total_experiments(self) -> int:
        """Calculate total number of experiments."""
        return len(self.systems) * len(self.models) * len(self.tickers) * len(self.tasks)


class MultiModelExperimentRunner:
    """
    Run experiments across multiple models and systems systematically.

    Orchestrates:
    1. Running each system (agent, RAG, zero-shot) with multiple LLMs
    2. Collecting comprehensive metrics for each run
    3. Recording predictions for ground truth validation
    4. Performing statistical analysis across models
    5. Generating publication-quality comparison reports
    """

    def __init__(
        self,
        output_dir: Optional[str] = None,
        enable_caching: bool = True,
    ):
        """
        Initialize multi-model runner.

        Args:
            output_dir: Directory for results
            enable_caching: Whether to cache results to avoid re-runs
        """
        self.output_dir = Path(output_dir or "./experiment_results_multimodel")
        self.output_dir.mkdir(exist_ok=True)

        self.metrics_collector = MetricsCollector(output_dir=str(self.output_dir / "metrics"))
        self.ground_truth_validator = GroundTruthValidator(
            storage_dir=str(self.output_dir / "ground_truth")
        )
        self.statistical_analyzer = StatisticalAnalyzer(alpha=0.05)

        self.enable_caching = enable_caching
        self.cache_file = self.output_dir / "experiment_cache.json"
        self.cache = self._load_cache()

        logger.info(f"MultiModelExperimentRunner initialized: output={self.output_dir}")

    def _load_cache(self) -> Dict[str, Any]:
        """Load experiment cache if exists."""
        if not self.enable_caching or not self.cache_file.exists():
            return {}

        try:
            with open(self.cache_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load cache: {e}")
            return {}

    def _save_cache(self):
        """Save experiment cache."""
        if not self.enable_caching:
            return

        try:
            with open(self.cache_file, "w") as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save cache: {e}")

    def run_single_experiment(
        self,
        system: str,
        model: ModelConfig,
        ticker: str,
        task: Dict[str, str],
        experiment_id: Optional[str] = None,
    ) -> MetricSnapshot:
        """
        Run a single experiment.

        Args:
            system: System type ("agent", "rag", "zeroshot")
            model: Model configuration
            ticker: Stock ticker
            task: Task dict with "name" and "prompt"
            experiment_id: Optional custom experiment ID

        Returns:
            MetricSnapshot with results
        """
        if experiment_id is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            experiment_id = f"{system}_{model.name}_{ticker}_{task['name']}_{timestamp}"

        # Check cache
        cache_key = f"{system}_{model.model_id}_{ticker}_{task['name']}"
        if self.enable_caching and cache_key in self.cache:
            logger.debug(f"Using cached result for {cache_key}")
            # Return cached metric
            cached = self.cache[cache_key]
            # Reconstruct MetricSnapshot from dict
            return MetricSnapshot(**cached)

        logger.info(
            f"Running: {system} + {model.name} on {ticker} - {task['name']}"
        )

        # Start measurement
        metric = self.metrics_collector.start_measurement(
            experiment_id=experiment_id,
            system_name=f"{system}_{model.name}",
            ticker=ticker,
            task_name=task['name'],
        )

        try:
            # Run the actual experiment based on system type
            if system == "agent":
                response = self._run_agent(model, ticker, task)
            elif system == "rag":
                response = self._run_rag(model, ticker, task)
            elif system == "zeroshot":
                response = self._run_zeroshot(model, ticker, task)
            else:
                raise ValueError(f"Unknown system: {system}")

            # Record response
            metric.set_response(response)

            # Extract and record prediction for ground truth validation
            prediction = self._extract_prediction(response, ticker)
            if prediction:
                self.ground_truth_validator.record_prediction(
                    system_name=system,
                    model_name=model.name,
                    ticker=ticker,
                    task_name=task['name'],
                    response_text=response,
                    prediction_type=PredictionType.PERCENT_CHANGE,
                    predicted_value=prediction,
                    timeframe_days=7,
                )

        except Exception as e:
            logger.error(f"Experiment failed: {e}")
            metric.error_occurred = True
            metric.error_message = str(e)

        finally:
            self.metrics_collector.end_measurement(metric)

        # Cache result
        if self.enable_caching:
            self.cache[cache_key] = metric.to_dict()
            self._save_cache()

        return metric

    def _run_agent(
        self,
        model: ModelConfig,
        ticker: str,
        task: Dict[str, str],
    ) -> str:
        """
        Run agent system with specified model.

        Args:
            model: Model configuration
            ticker: Stock ticker
            task: Task dict

        Returns:
            Response text
        """
        # Import here to avoid circular dependency
        from finrobot.experiments.experiment_runner import FinRobotExperimentRunner

        runner = FinRobotExperimentRunner()
        metric = runner.run_agent_analysis(
            ticker=ticker,
            task_prompt=task['prompt'],
            model=model.model_id,
            temperature=model.temperature,
            task_name=task['name'],
        )

        return metric.response_text

    def _run_rag(
        self,
        model: ModelConfig,
        ticker: str,
        task: Dict[str, str],
    ) -> str:
        """
        Run RAG system with specified model.

        Args:
            model: Model configuration
            ticker: Stock ticker
            task: Task dict

        Returns:
            Response text
        """
        from finrobot.experiments.rag_system import RAGChain
        from finrobot.data_source import YFinanceUtils

        # Fetch stock data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)

        stock_data = YFinanceUtils.get_stock_data(
            ticker,
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d"),
        )

        # Run RAG
        rag = RAGChain()
        response = rag.query(
            query=task['prompt'],
            ticker=ticker,
            stock_data=stock_data,
        )

        return response

    def _run_zeroshot(
        self,
        model: ModelConfig,
        ticker: str,
        task: Dict[str, str],
    ) -> str:
        """
        Run zero-shot LLM with specified model (no tools, no RAG).

        Args:
            model: Model configuration
            ticker: Stock ticker
            task: Task dict

        Returns:
            Response text
        """
        # Simple LLM call without tools
        prompt = f"""
{task['prompt']}

Stock ticker: {ticker}

Provide your analysis based on your general knowledge.
Do not use any external tools or data sources.
"""

        # Use appropriate API based on provider
        if model.provider == ModelProvider.OPENAI:
            return self._call_openai(model, prompt)
        elif model.provider == ModelProvider.ANTHROPIC:
            return self._call_anthropic(model, prompt)
        else:
            # Default fallback
            return "Zero-shot analysis not yet implemented for this model"

    def _call_openai(self, model: ModelConfig, prompt: str) -> str:
        """Call OpenAI API."""
        try:
            import openai
            import os

            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            response = client.chat.completions.create(
                model=model.model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=model.temperature,
                max_tokens=model.max_tokens,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            return f"Error: {str(e)}"

    def _call_anthropic(self, model: ModelConfig, prompt: str) -> str:
        """Call Anthropic API."""
        try:
            import anthropic
            import os

            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

            response = client.messages.create(
                model=model.model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=model.temperature,
                max_tokens=model.max_tokens,
            )

            return response.content[0].text

        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}")
            return f"Error: {str(e)}"

    def _extract_prediction(self, response: str, ticker: str) -> Optional[str]:
        """
        Extract prediction from response text.

        Args:
            response: Response text
            ticker: Stock ticker

        Returns:
            Extracted prediction string or None
        """
        from finrobot.experiments.fact_checker import StockClaimExtractor

        extractor = StockClaimExtractor()
        prediction = extractor.extract_price_prediction(response)

        if prediction:
            percent, direction = prediction
            if percent:
                return f"{direction} {percent}%"
            else:
                return direction

        return None

    def run_experiment_plan(self, plan: ExperimentPlan) -> Dict[str, List[MetricSnapshot]]:
        """
        Execute comprehensive experiment plan.

        Args:
            plan: ExperimentPlan with all configurations

        Returns:
            Dict mapping system_model keys to list of metrics
        """
        total = plan.total_experiments()
        current = 0
        results = {}

        logger.info(f"Starting experiment plan: {total} total experiments")
        print(f"\n{'='*80}")
        print(f"EXPERIMENT PLAN: {total} experiments")
        print(f"Systems: {plan.systems}")
        print(f"Models: {[m.name for m in plan.models]}")
        print(f"Stocks: {len(plan.tickers)}")
        print(f"Tasks: {len(plan.tasks)}")
        print(f"{'='*80}\n")

        for system in plan.systems:
            for model in plan.models:
                key = f"{system}_{model.name}"
                results[key] = []

                for ticker in plan.tickers:
                    for task in plan.tasks:
                        current += 1
                        print(f"\n[{current}/{total}] {system} + {model.name} | {ticker} | {task['name']}")

                        try:
                            metric = self.run_single_experiment(
                                system=system,
                                model=model,
                                ticker=ticker,
                                task=task,
                            )
                            results[key].append(metric)

                            print(f"  ✓ Completed in {metric.latency_seconds:.2f}s")

                        except Exception as e:
                            logger.error(f"Failed: {e}")
                            print(f"  ✗ Failed: {e}")
                            continue

        logger.info(f"Experiment plan complete: {current} experiments run")
        return results

    def analyze_results(
        self,
        results: Dict[str, List[MetricSnapshot]],
    ) -> Dict[str, Any]:
        """
        Perform comprehensive statistical analysis.

        Args:
            results: Results from run_experiment_plan

        Returns:
            Analysis report dict
        """
        logger.info("Performing statistical analysis...")

        # Group by system and model
        metrics_by_system = {}
        for key, metrics in results.items():
            metrics_by_system[key] = metrics

        # Statistical comparison
        comparison_report = self.statistical_analyzer.compare_multiple_systems(
            metrics_by_system
        )

        # Ground truth validation
        validation_reports = {}
        for key in results.keys():
            system = key.split('_')[0]
            model = '_'.join(key.split('_')[1:])
            report = self.ground_truth_validator.generate_report(
                system_filter=system,
                model_filter=model,
            )
            validation_reports[key] = report

        analysis = {
            "statistical_comparison": comparison_report.to_dict(),
            "validation_reports": {k: v.to_dict() for k, v in validation_reports.items()},
            "summary": {
                "total_experiments": sum(len(m) for m in results.values()),
                "systems_compared": list(set(k.split('_')[0] for k in results.keys())),
                "models_compared": list(set('_'.join(k.split('_')[1:]) for k in results.keys())),
            }
        }

        # Save analysis
        analysis_path = self.output_dir / f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(analysis_path, "w") as f:
            json.dump(analysis, f, indent=2)

        logger.info(f"Analysis saved to {analysis_path}")

        return analysis

    def print_summary(self, analysis: Dict[str, Any]):
        """Print human-readable summary."""
        print("\n" + "=" * 80)
        print("MULTI-MODEL EXPERIMENT SUMMARY")
        print("=" * 80)

        summary = analysis['summary']
        print(f"\nTotal Experiments: {summary['total_experiments']}")
        print(f"Systems: {', '.join(summary['systems_compared'])}")
        print(f"Models: {', '.join(summary['models_compared'])}")

        print("\n" + "-" * 80)
        print("STATISTICAL RESULTS")
        print("-" * 80)

        comp = analysis['statistical_comparison']
        print(f"Overall Best System: {comp['overall_best_system']}")
        print(f"Confidence: {comp['confidence_score']:.1%}")

        print("\n" + "-" * 80)
        print("GROUND TRUTH VALIDATION")
        print("-" * 80)

        for key, report in analysis['validation_reports'].items():
            if report['validated_predictions'] == 0:
                continue
            print(f"\n{key}:")
            print(f"  Accuracy: {report['overall_accuracy']:.3f}")
            print(f"  Directional Accuracy: {report['directional_accuracy']:.1%}")
            print(f"  Mean Error: {report['mean_magnitude_error']:.2f}%")

        print("\n" + "=" * 80)


def create_comprehensive_plan(
    quick_test: bool = False,
) -> ExperimentPlan:
    """
    Create comprehensive experiment plan.

    Args:
        quick_test: If True, use minimal config for testing

    Returns:
        ExperimentPlan
    """
    from datetime import timedelta

    if quick_test:
        # Quick test: 2 systems, 2 models, 2 stocks, 2 tasks = 16 experiments
        return ExperimentPlan(
            systems=["agent", "rag"],
            models=[ModelConfig.gpt4(), ModelConfig.claude_35_sonnet()],
            tickers=["AAPL", "MSFT"],
            tasks=[
                {
                    "name": "price_prediction",
                    "prompt": "Predict the stock price movement for the next week.",
                },
                {
                    "name": "risk_analysis",
                    "prompt": "Identify the top 2-3 risk factors for this stock.",
                },
            ],
        )
    else:
        # Full plan: 3 systems, 3 models, 30 stocks, 3 tasks = 810 experiments
        return ExperimentPlan(
            systems=["agent", "rag", "zeroshot"],
            models=[
                ModelConfig.gpt4(),
                ModelConfig.claude_35_sonnet(),
                ModelConfig.llama_70b(),
            ],
            tickers=[
                # Tech
                "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "NFLX", "AMD", "INTC",
                # Finance
                "JPM", "BAC", "GS", "MS", "C", "WFC",
                # Healthcare
                "JNJ", "UNH", "PFE", "ABBV", "LLY", "MRK",
                # Consumer
                "WMT", "HD", "MCD", "NKE", "SBUX",
                # Energy
                "XOM", "CVX", "COP",
            ],
            tasks=[
                {
                    "name": "price_prediction",
                    "prompt": "Analyze the stock and predict price movement for the next week (direction and percentage).",
                },
                {
                    "name": "risk_analysis",
                    "prompt": "Identify the top 2-3 risk factors based on recent data.",
                },
                {
                    "name": "opportunity_analysis",
                    "prompt": "Identify investment opportunities and provide specific recommendations.",
                },
            ],
        )
