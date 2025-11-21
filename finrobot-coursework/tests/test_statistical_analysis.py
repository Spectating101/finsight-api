"""
Tests for statistical analysis module.
"""

import pytest
import numpy as np
from pathlib import Path
import tempfile

from finrobot.experiments.statistical_analysis import (
    StatisticalAnalyzer,
    TTestResult,
    ANOVAResult,
    ComparisonReport,
)
from finrobot.experiments.metrics_collector import MetricSnapshot


@pytest.fixture
def analyzer():
    """Create analyzer instance."""
    return StatisticalAnalyzer(alpha=0.05)


@pytest.fixture
def sample_metrics():
    """Create sample metrics for testing."""
    # System 1: Fast but less thorough
    metrics1 = [
        MetricSnapshot(
            experiment_id=f"exp1_{i}",
            system_name="system1",
            ticker="AAPL",
            task_name="test",
            latency_seconds=2.0 + np.random.normal(0, 0.5),
            total_cost=0.05 + np.random.normal(0, 0.01),
            tool_calls_count=3,
            reasoning_steps=5,
            response_length=500,
        )
        for i in range(20)
    ]

    # System 2: Slower but more thorough
    metrics2 = [
        MetricSnapshot(
            experiment_id=f"exp2_{i}",
            system_name="system2",
            ticker="AAPL",
            task_name="test",
            latency_seconds=4.0 + np.random.normal(0, 0.5),
            total_cost=0.10 + np.random.normal(0, 0.01),
            tool_calls_count=7,
            reasoning_steps=12,
            response_length=1200,
        )
        for i in range(20)
    ]

    return metrics1, metrics2


def test_analyzer_initialization():
    """Test analyzer initializes correctly."""
    analyzer = StatisticalAnalyzer(alpha=0.05)
    assert analyzer.alpha == 0.05

    analyzer = StatisticalAnalyzer(alpha=0.01)
    assert analyzer.alpha == 0.01


def test_ttest_independent(analyzer):
    """Test independent t-test."""
    group1 = [1.0, 2.0, 3.0, 4.0, 5.0]
    group2 = [3.0, 4.0, 5.0, 6.0, 7.0]

    result = analyzer.ttest(
        group1, group2,
        "group1", "group2",
        "test_metric",
        paired=False
    )

    assert result.group1_name == "group1"
    assert result.group2_name == "group2"
    assert result.metric_name == "test_metric"
    assert result.n1 == 5
    assert result.n2 == 5
    assert result.mean1 == 3.0
    assert result.mean2 == 5.0
    assert result.test_type == "independent"
    assert result.t_statistic < 0  # group1 mean < group2 mean
    assert 0 <= result.p_value <= 1


def test_ttest_paired(analyzer):
    """Test paired t-test."""
    group1 = [1.0, 2.0, 3.0, 4.0, 5.0]
    group2 = [1.5, 2.5, 3.5, 4.5, 5.5]

    result = analyzer.ttest(
        group1, group2,
        "before", "after",
        "score",
        paired=True
    )

    assert result.test_type == "paired"
    assert result.n1 == result.n2 == 5
    assert result.is_significant  # Should be significant


def test_cohens_d_calculation(analyzer):
    """Test Cohen's d effect size calculation."""
    # Large effect size
    group1 = np.array([1.0, 2.0, 3.0])
    group2 = np.array([5.0, 6.0, 7.0])

    d = analyzer._calculate_cohens_d(group1, group2, paired=False)
    assert abs(d) > 0.8  # Large effect

    # Small effect size
    group1 = np.array([1.0, 2.0, 3.0])
    group2 = np.array([1.1, 2.1, 3.1])

    d = analyzer._calculate_cohens_d(group1, group2, paired=False)
    assert abs(d) < 0.5  # Small effect


def test_significance_levels(analyzer):
    """Test significance level assignment."""
    # Highly significant
    group1 = [1.0] * 30
    group2 = [5.0] * 30

    result = analyzer.ttest(group1, group2, "g1", "g2", "metric", paired=False)
    assert result.is_significant
    assert result.significance_level == "***"

    # Not significant
    group1 = [3.0 + np.random.normal(0, 1) for _ in range(10)]
    group2 = [3.1 + np.random.normal(0, 1) for _ in range(10)]

    result = analyzer.ttest(group1, group2, "g1", "g2", "metric", paired=False)
    # May or may not be significant, but shouldn't crash
    assert result.significance_level in ["***", "**", "*", "ns"]


def test_compare_two_systems(analyzer, sample_metrics):
    """Test comparing two systems."""
    metrics1, metrics2 = sample_metrics

    results = analyzer.compare_two_systems(
        metrics1, metrics2,
        "system1", "system2",
        paired=False
    )

    # Should have results for multiple metrics
    assert "latency_seconds" in results
    assert "total_cost" in results
    assert "tool_calls_count" in results

    # Check latency comparison
    latency_result = results["latency_seconds"]
    assert latency_result.mean1 < latency_result.mean2  # system1 is faster
    assert latency_result.is_significant  # Should be significantly different


def test_anova(analyzer):
    """Test ANOVA for multiple groups."""
    groups = {
        "group1": [1.0, 2.0, 3.0, 4.0, 5.0],
        "group2": [3.0, 4.0, 5.0, 6.0, 7.0],
        "group3": [5.0, 6.0, 7.0, 8.0, 9.0],
    }

    result = analyzer.anova(groups, "test_metric", posthoc=True)

    assert result.metric_name == "test_metric"
    assert len(result.groups) == 3
    assert result.f_statistic > 0
    assert 0 <= result.p_value <= 1
    assert result.is_significant  # Groups are clearly different

    # Check post-hoc comparisons
    assert len(result.posthoc_comparisons) == 3  # 3 pairwise comparisons


def test_anova_no_posthoc(analyzer):
    """Test ANOVA without post-hoc tests."""
    groups = {
        "group1": [1.0, 2.0, 3.0],
        "group2": [4.0, 5.0, 6.0],
    }

    result = analyzer.anova(groups, "metric", posthoc=False)
    assert len(result.posthoc_comparisons) == 0


def test_compare_multiple_systems(analyzer, sample_metrics):
    """Test comprehensive multi-system comparison."""
    metrics1, metrics2 = sample_metrics

    # Add a third system
    metrics3 = [
        MetricSnapshot(
            experiment_id=f"exp3_{i}",
            system_name="system3",
            ticker="AAPL",
            task_name="test",
            latency_seconds=3.0 + np.random.normal(0, 0.5),
            total_cost=0.07 + np.random.normal(0, 0.01),
            tool_calls_count=5,
            reasoning_steps=8,
            response_length=800,
        )
        for i in range(20)
    ]

    metrics_by_system = {
        "system1": metrics1,
        "system2": metrics2,
        "system3": metrics3,
    }

    report = analyzer.compare_multiple_systems(metrics_by_system)

    assert len(report.systems_compared) == 3
    assert report.total_experiments == 60  # 20 * 3
    assert len(report.ttests) > 0  # Should have pairwise comparisons
    assert len(report.anova_results) > 0  # Should have ANOVA for each metric
    assert report.overall_best_system in ["system1", "system2", "system3"]
    assert 0 <= report.confidence_score <= 1


def test_winner_determination(analyzer):
    """Test that winner is correctly determined."""
    # System1: faster and cheaper
    metrics1 = [
        MetricSnapshot(
            experiment_id=f"exp1_{i}",
            system_name="fast_cheap",
            ticker="AAPL",
            task_name="test",
            latency_seconds=1.0,
            total_cost=0.01,
            tool_calls_count=2,
            reasoning_steps=3,
            response_length=300,
        )
        for i in range(10)
    ]

    # System2: slower and expensive
    metrics2 = [
        MetricSnapshot(
            experiment_id=f"exp2_{i}",
            system_name="slow_expensive",
            ticker="AAPL",
            task_name="test",
            latency_seconds=5.0,
            total_cost=0.20,
            tool_calls_count=10,
            reasoning_steps=15,
            response_length=1500,
        )
        for i in range(10)
    ]

    report = analyzer.compare_multiple_systems({
        "fast_cheap": metrics1,
        "slow_expensive": metrics2,
    })

    # fast_cheap should win on latency and cost
    assert report.winner_by_metric.get("latency_seconds") == "fast_cheap"
    assert report.winner_by_metric.get("total_cost") == "fast_cheap"

    # slow_expensive should win on thoroughness
    assert report.winner_by_metric.get("tool_calls_count") == "slow_expensive"
    assert report.winner_by_metric.get("reasoning_steps") == "slow_expensive"


def test_extract_metric_values(analyzer):
    """Test extracting metric values from snapshots."""
    metrics = [
        MetricSnapshot(
            experiment_id="1",
            system_name="test",
            ticker="AAPL",
            task_name="task",
            latency_seconds=2.5,
        ),
        MetricSnapshot(
            experiment_id="2",
            system_name="test",
            ticker="MSFT",
            task_name="task",
            latency_seconds=3.0,
        ),
        # Error case - should be excluded
        MetricSnapshot(
            experiment_id="3",
            system_name="test",
            ticker="GOOGL",
            task_name="task",
            latency_seconds=1.0,
            error_occurred=True,
        ),
    ]

    values = analyzer._extract_metric_values(metrics, "latency_seconds")

    assert len(values) == 2  # Error case excluded
    assert 2.5 in values
    assert 3.0 in values
    assert 1.0 not in values  # Error case


def test_export_report(analyzer, sample_metrics):
    """Test exporting report to JSON."""
    metrics1, metrics2 = sample_metrics
    report = analyzer.compare_multiple_systems({
        "system1": metrics1,
        "system2": metrics2,
    })

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        output_path = Path(f.name)

    try:
        analyzer.export_report(report, output_path)
        assert output_path.exists()

        # Verify it's valid JSON
        import json
        with open(output_path, "r") as f:
            data = json.load(f)

        assert "systems_compared" in data
        assert "ttests" in data
    finally:
        if output_path.exists():
            output_path.unlink()


def test_confidence_intervals(analyzer):
    """Test confidence interval calculation."""
    group1 = [5.0, 6.0, 7.0, 8.0, 9.0] * 10  # n=50
    group2 = [6.0, 7.0, 8.0, 9.0, 10.0] * 10

    result = analyzer.ttest(group1, group2, "g1", "g2", "metric", paired=False)

    # CI should bracket mean difference
    mean_diff = result.mean1 - result.mean2
    ci_95_lower, ci_95_upper = result.ci_95

    # The mean difference should be within CI (or very close due to calculation)
    # For paired test: CI is for the mean difference
    # For independent test: CI is for difference in means
    assert ci_95_lower < mean_diff < ci_95_upper or abs(ci_95_lower - mean_diff) < 0.01

    # 99% CI should be wider than 95% CI
    ci_99_lower, ci_99_upper = result.ci_99
    assert ci_99_upper - ci_99_lower > ci_95_upper - ci_95_lower


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
