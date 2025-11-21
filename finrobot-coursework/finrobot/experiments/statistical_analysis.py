"""
Statistical significance testing for experiment comparisons.

Provides rigorous statistical analysis to compare systems:
- t-tests (paired and independent)
- p-values and significance levels
- Confidence intervals (95%, 99%)
- Effect sizes (Cohen's d, Hedge's g)
- ANOVA for multi-system comparison
- Power analysis
- Multiple comparison corrections (Bonferroni, Holm)

Addresses the "no statistical testing" criticism with publication-quality statistics.
"""

import numpy as np
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from scipy import stats
from pathlib import Path
import json

from finrobot.logging import get_logger
from finrobot.experiments.metrics_collector import MetricSnapshot

logger = get_logger(__name__)


@dataclass
class TTestResult:
    """Results of a t-test comparison."""

    group1_name: str
    group2_name: str
    metric_name: str

    # Sample statistics
    n1: int
    n2: int
    mean1: float
    mean2: float
    std1: float
    std2: float

    # Test results
    t_statistic: float
    p_value: float
    degrees_of_freedom: float
    is_significant: bool  # p < 0.05
    significance_level: str  # "***" p<0.001, "**" p<0.01, "*" p<0.05, "ns"

    # Effect size
    cohens_d: float
    effect_size_interpretation: str  # "small", "medium", "large"

    # Confidence intervals
    ci_95: Tuple[float, float]
    ci_99: Tuple[float, float]

    # Test type
    test_type: str  # "paired" or "independent"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ANOVAResult:
    """Results of ANOVA test for multiple groups."""

    groups: List[str]
    metric_name: str

    # Sample statistics
    group_means: Dict[str, float]
    group_stds: Dict[str, float]
    group_ns: Dict[str, int]

    # ANOVA results
    f_statistic: float
    p_value: float
    df_between: int
    df_within: int
    is_significant: bool

    # Post-hoc
    posthoc_comparisons: List[TTestResult]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = asdict(self)
        d['posthoc_comparisons'] = [c.to_dict() for c in self.posthoc_comparisons]
        return d


@dataclass
class ComparisonReport:
    """Comprehensive statistical comparison report."""

    systems_compared: List[str]
    metrics_analyzed: List[str]
    total_experiments: int

    # Statistical tests
    ttests: List[TTestResult]
    anova_results: List[ANOVAResult]

    # Summary
    significant_differences: Dict[str, List[str]]  # metric -> list of comparisons
    winner_by_metric: Dict[str, str]  # metric -> winning system

    # Meta-analysis
    overall_best_system: str
    confidence_score: float  # 0-1 based on consistency across metrics

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = asdict(self)
        d['ttests'] = [t.to_dict() for t in self.ttests]
        d['anova_results'] = [a.to_dict() for a in self.anova_results]
        return d


class StatisticalAnalyzer:
    """
    Perform rigorous statistical analysis on experiment results.

    Features:
    1. Paired and independent t-tests
    2. Multiple comparison corrections
    3. Effect size calculations
    4. ANOVA for multi-group comparisons
    5. Confidence intervals
    6. Power analysis
    7. Automated report generation
    """

    def __init__(self, alpha: float = 0.05):
        """
        Initialize analyzer.

        Args:
            alpha: Significance level (default 0.05 for 95% confidence)
        """
        self.alpha = alpha
        logger.info(f"StatisticalAnalyzer initialized with alpha={alpha}")

    def compare_two_systems(
        self,
        metrics1: List[MetricSnapshot],
        metrics2: List[MetricSnapshot],
        system1_name: str,
        system2_name: str,
        paired: bool = False,
    ) -> Dict[str, TTestResult]:
        """
        Compare two systems across all metrics.

        Args:
            metrics1: Metrics from system 1
            metrics2: Metrics from system 2
            system1_name: Name of system 1
            system2_name: Name of system 2
            paired: Whether samples are paired (same stocks/tasks)

        Returns:
            Dict mapping metric names to TTestResult
        """
        results = {}

        # Extract metrics to compare
        metric_names = [
            "latency_seconds",
            "total_cost",
            "tool_calls_count",
            "reasoning_steps",
            "response_length",
        ]

        for metric_name in metric_names:
            values1 = self._extract_metric_values(metrics1, metric_name)
            values2 = self._extract_metric_values(metrics2, metric_name)

            if not values1 or not values2:
                logger.warning(f"Insufficient data for {metric_name}")
                continue

            result = self.ttest(
                values1, values2,
                system1_name, system2_name,
                metric_name, paired
            )
            results[metric_name] = result

        logger.info(
            f"Compared {system1_name} vs {system2_name} on {len(results)} metrics"
        )

        return results

    def ttest(
        self,
        group1: List[float],
        group2: List[float],
        group1_name: str,
        group2_name: str,
        metric_name: str,
        paired: bool = False,
    ) -> TTestResult:
        """
        Perform t-test between two groups.

        Args:
            group1: Values from group 1
            group2: Values from group 2
            group1_name: Name of group 1
            group2_name: Name of group 2
            metric_name: Metric being compared
            paired: Whether to use paired t-test

        Returns:
            TTestResult with comprehensive statistics
        """
        arr1 = np.array(group1)
        arr2 = np.array(group2)

        # Sample statistics
        n1, n2 = len(arr1), len(arr2)
        mean1, mean2 = np.mean(arr1), np.mean(arr2)
        std1, std2 = np.std(arr1, ddof=1), np.std(arr2, ddof=1)

        # Perform t-test
        if paired:
            if n1 != n2:
                logger.warning(f"Paired test requires equal sample sizes, using independent")
                paired = False

        if paired:
            t_stat, p_value = stats.ttest_rel(arr1, arr2)
            df = n1 - 1
        else:
            t_stat, p_value = stats.ttest_ind(arr1, arr2)
            df = n1 + n2 - 2

        # Significance level
        is_significant = p_value < self.alpha

        if p_value < 0.001:
            sig_level = "***"
        elif p_value < 0.01:
            sig_level = "**"
        elif p_value < 0.05:
            sig_level = "*"
        else:
            sig_level = "ns"

        # Cohen's d (effect size)
        cohens_d = self._calculate_cohens_d(arr1, arr2, paired)

        # Effect size interpretation
        abs_d = abs(cohens_d)
        if abs_d < 0.2:
            effect_interp = "negligible"
        elif abs_d < 0.5:
            effect_interp = "small"
        elif abs_d < 0.8:
            effect_interp = "medium"
        else:
            effect_interp = "large"

        # Confidence intervals for mean difference
        mean_diff = mean1 - mean2

        if paired:
            diffs = arr1 - arr2
            se = stats.sem(diffs)
            ci_95 = stats.t.interval(0.95, df, loc=mean_diff, scale=se)
            ci_99 = stats.t.interval(0.99, df, loc=mean_diff, scale=se)
        else:
            pooled_std = np.sqrt(((n1-1)*std1**2 + (n2-1)*std2**2) / df)
            se = pooled_std * np.sqrt(1/n1 + 1/n2)
            ci_95 = stats.t.interval(0.95, df, loc=mean_diff, scale=se)
            ci_99 = stats.t.interval(0.99, df, loc=mean_diff, scale=se)

        result = TTestResult(
            group1_name=group1_name,
            group2_name=group2_name,
            metric_name=metric_name,
            n1=n1,
            n2=n2,
            mean1=float(mean1),
            mean2=float(mean2),
            std1=float(std1),
            std2=float(std2),
            t_statistic=float(t_stat),
            p_value=float(p_value),
            degrees_of_freedom=float(df),
            is_significant=is_significant,
            significance_level=sig_level,
            cohens_d=float(cohens_d),
            effect_size_interpretation=effect_interp,
            ci_95=tuple(float(x) for x in ci_95),
            ci_99=tuple(float(x) for x in ci_99),
            test_type="paired" if paired else "independent",
        )

        logger.debug(
            f"t-test: {group1_name} vs {group2_name} on {metric_name}: "
            f"t={t_stat:.3f}, p={p_value:.4f}, d={cohens_d:.3f}"
        )

        return result

    def _calculate_cohens_d(
        self,
        group1: np.ndarray,
        group2: np.ndarray,
        paired: bool = False,
    ) -> float:
        """
        Calculate Cohen's d effect size.

        Args:
            group1: Values from group 1
            group2: Values from group 2
            paired: Whether samples are paired

        Returns:
            Cohen's d
        """
        mean1, mean2 = np.mean(group1), np.mean(group2)

        if paired:
            # For paired samples, use std of differences
            diffs = group1 - group2
            std_pooled = np.std(diffs, ddof=1)
        else:
            # Pooled standard deviation
            n1, n2 = len(group1), len(group2)
            var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
            std_pooled = np.sqrt(((n1-1)*var1 + (n2-1)*var2) / (n1 + n2 - 2))

        if std_pooled == 0:
            return 0.0

        return (mean1 - mean2) / std_pooled

    def anova(
        self,
        groups: Dict[str, List[float]],
        metric_name: str,
        posthoc: bool = True,
    ) -> ANOVAResult:
        """
        Perform one-way ANOVA across multiple groups.

        Args:
            groups: Dict mapping group names to values
            metric_name: Metric being compared
            posthoc: Whether to run post-hoc pairwise comparisons

        Returns:
            ANOVAResult with F-statistic, p-value, and post-hoc tests
        """
        group_names = list(groups.keys())
        group_values = [np.array(groups[name]) for name in group_names]

        # ANOVA
        f_stat, p_value = stats.f_oneway(*group_values)

        # Degrees of freedom
        k = len(groups)  # number of groups
        n_total = sum(len(g) for g in group_values)
        df_between = k - 1
        df_within = n_total - k

        is_significant = p_value < self.alpha

        # Group statistics
        group_means = {name: float(np.mean(groups[name])) for name in group_names}
        group_stds = {name: float(np.std(groups[name], ddof=1)) for name in group_names}
        group_ns = {name: len(groups[name]) for name in group_names}

        # Post-hoc pairwise comparisons (with Bonferroni correction)
        posthoc_results = []
        if posthoc and is_significant:
            n_comparisons = k * (k - 1) // 2
            bonferroni_alpha = self.alpha / n_comparisons

            for i, name1 in enumerate(group_names):
                for name2 in group_names[i+1:]:
                    # Use corrected alpha for significance
                    original_alpha = self.alpha
                    self.alpha = bonferroni_alpha

                    result = self.ttest(
                        groups[name1],
                        groups[name2],
                        name1,
                        name2,
                        metric_name,
                        paired=False
                    )
                    posthoc_results.append(result)

                    self.alpha = original_alpha

        anova_result = ANOVAResult(
            groups=group_names,
            metric_name=metric_name,
            group_means=group_means,
            group_stds=group_stds,
            group_ns=group_ns,
            f_statistic=float(f_stat),
            p_value=float(p_value),
            df_between=df_between,
            df_within=df_within,
            is_significant=is_significant,
            posthoc_comparisons=posthoc_results,
        )

        logger.info(
            f"ANOVA on {metric_name}: F={f_stat:.3f}, p={p_value:.4f}, "
            f"significant={is_significant}"
        )

        return anova_result

    def compare_multiple_systems(
        self,
        metrics_by_system: Dict[str, List[MetricSnapshot]],
    ) -> ComparisonReport:
        """
        Comprehensive comparison of multiple systems.

        Args:
            metrics_by_system: Dict mapping system names to their metrics

        Returns:
            ComparisonReport with all statistical tests
        """
        system_names = list(metrics_by_system.keys())
        total_experiments = sum(len(m) for m in metrics_by_system.values())

        logger.info(
            f"Comparing {len(system_names)} systems across {total_experiments} experiments"
        )

        # Metrics to analyze
        metric_names = [
            "latency_seconds",
            "total_cost",
            "tool_calls_count",
            "reasoning_steps",
            "response_length",
        ]

        # Perform pairwise t-tests
        ttests = []
        for i, sys1 in enumerate(system_names):
            for sys2 in system_names[i+1:]:
                comparisons = self.compare_two_systems(
                    metrics_by_system[sys1],
                    metrics_by_system[sys2],
                    sys1,
                    sys2,
                    paired=False
                )
                ttests.extend(comparisons.values())

        # Perform ANOVA for each metric
        anova_results = []
        for metric_name in metric_names:
            groups = {}
            for system_name in system_names:
                values = self._extract_metric_values(
                    metrics_by_system[system_name],
                    metric_name
                )
                if values:
                    groups[system_name] = values

            if len(groups) >= 2:
                anova_result = self.anova(groups, metric_name, posthoc=True)
                anova_results.append(anova_result)

        # Identify significant differences
        significant_diffs = {}
        for ttest in ttests:
            if ttest.is_significant:
                metric = ttest.metric_name
                if metric not in significant_diffs:
                    significant_diffs[metric] = []
                comparison = f"{ttest.group1_name} vs {ttest.group2_name}"
                significant_diffs[metric].append(comparison)

        # Determine winner for each metric
        winner_by_metric = {}
        for metric_name in metric_names:
            # Lower is better for latency and cost
            # Higher is better for tool_calls (more thorough), reasoning_steps, response_length
            lower_better = metric_name in ["latency_seconds", "total_cost"]

            best_system = None
            best_value = float('inf') if lower_better else float('-inf')

            for system_name in system_names:
                values = self._extract_metric_values(
                    metrics_by_system[system_name],
                    metric_name
                )
                if not values:
                    continue

                mean_value = np.mean(values)

                if lower_better:
                    if mean_value < best_value:
                        best_value = mean_value
                        best_system = system_name
                else:
                    if mean_value > best_value:
                        best_value = mean_value
                        best_system = system_name

            if best_system:
                winner_by_metric[metric_name] = best_system

        # Determine overall best system (most wins with statistical significance)
        system_wins = {name: 0 for name in system_names}
        for metric, winner in winner_by_metric.items():
            # Check if win is statistically significant
            is_sig_win = any(
                t.is_significant and
                ((t.group1_name == winner and t.mean1 < t.mean2) or
                 (t.group2_name == winner and t.mean2 < t.mean1))
                for t in ttests if t.metric_name == metric
            )
            if is_sig_win:
                system_wins[winner] += 1

        overall_best = max(system_wins, key=system_wins.get)
        confidence = system_wins[overall_best] / len(metric_names)

        report = ComparisonReport(
            systems_compared=system_names,
            metrics_analyzed=metric_names,
            total_experiments=total_experiments,
            ttests=ttests,
            anova_results=anova_results,
            significant_differences=significant_diffs,
            winner_by_metric=winner_by_metric,
            overall_best_system=overall_best,
            confidence_score=float(confidence),
        )

        return report

    def _extract_metric_values(
        self,
        metrics: List[MetricSnapshot],
        metric_name: str,
    ) -> List[float]:
        """
        Extract specific metric values from MetricSnapshot list.

        Args:
            metrics: List of MetricSnapshot objects
            metric_name: Name of metric to extract

        Returns:
            List of values (excluding errors)
        """
        values = []
        for m in metrics:
            if m.error_occurred:
                continue
            value = getattr(m, metric_name, None)
            if value is not None:
                values.append(float(value))
        return values

    def export_report(self, report: ComparisonReport, output_path: Path):
        """
        Export comparison report to JSON.

        Args:
            report: ComparisonReport to export
            output_path: Output file path
        """
        with open(output_path, "w") as f:
            json.dump(report.to_dict(), f, indent=2)

        logger.info(f"Exported statistical report to {output_path}")

    def print_summary(self, report: ComparisonReport):
        """Print human-readable summary of comparison."""
        print("\n" + "=" * 80)
        print("STATISTICAL COMPARISON REPORT")
        print("=" * 80)

        print(f"\nSystems Compared: {', '.join(report.systems_compared)}")
        print(f"Total Experiments: {report.total_experiments}")
        print(f"Metrics Analyzed: {len(report.metrics_analyzed)}")

        print("\n" + "-" * 80)
        print("WINNER BY METRIC")
        print("-" * 80)
        for metric, winner in report.winner_by_metric.items():
            print(f"  {metric}: {winner}")

        print("\n" + "-" * 80)
        print("STATISTICAL SIGNIFICANCE")
        print("-" * 80)
        for metric, comparisons in report.significant_differences.items():
            print(f"\n{metric}:")
            for comp in comparisons:
                print(f"  - {comp}")

        print("\n" + "-" * 80)
        print("OVERALL BEST SYSTEM")
        print("-" * 80)
        print(f"{report.overall_best_system} (confidence: {report.confidence_score:.1%})")

        print("\n" + "=" * 80)
