"""
Phase 5: Statistical Analysis and Visualization

Analyzes experiment results and generates:
- Statistical comparison (t-tests, effect sizes)
- Performance charts (latency, cost, quality)
- Publication-quality figures for paper
- Detailed analysis report

Designed for academic rigor and A+ quality.
"""

import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, Any, List, Tuple
from scipy import stats
from datetime import datetime

# Set publication-quality style
sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['figure.dpi'] = 300

class ExperimentAnalyzer:
    """
    Sophisticated analysis of Agent vs RAG experiments.

    Features:
    - Statistical significance testing
    - Effect size calculation
    - Multi-dimensional comparison
    - Publication-quality visualizations
    - Comprehensive report generation
    """

    def __init__(self, results_file: str):
        """
        Initialize analyzer.

        Args:
            results_file: Path to results CSV file
        """
        self.results_file = Path(results_file)
        self.df = pd.read_csv(results_file)
        self.output_dir = self.results_file.parent / "analysis"
        self.output_dir.mkdir(exist_ok=True)

        # Filter successful experiments
        self.df_success = self.df[self.df["success"] == True].copy()

        print(f"Loaded {len(self.df)} experiments ({len(self.df_success)} successful)")
        print(f"Analysis output: {self.output_dir}")

    def run_full_analysis(self):
        """Run complete analysis pipeline."""
        print("\n" + "="*80)
        print("COMPREHENSIVE ANALYSIS")
        print("="*80 + "\n")

        # 1. Descriptive statistics
        print("1. Computing descriptive statistics...")
        desc_stats = self.compute_descriptive_statistics()

        # 2. Statistical tests
        print("2. Running statistical significance tests...")
        stat_tests = self.run_statistical_tests()

        # 3. Generate visualizations
        print("3. Generating visualizations...")
        self.generate_all_visualizations()

        # 4. Generate report
        print("4. Creating analysis report...")
        self.generate_report(desc_stats, stat_tests)

        print("\n✅ Analysis complete!")
        print(f"📊 Charts saved to: {self.output_dir}")
        print(f"📄 Report saved to: {self.output_dir / 'analysis_report.txt'}")

    def compute_descriptive_statistics(self) -> Dict[str, Any]:
        """Compute descriptive statistics for both systems."""
        stats_dict = {}

        for system in ["agent", "rag"]:
            system_df = self.df_success[self.df_success["system"] == system]

            if system_df.empty:
                continue

            stats_dict[system] = {
                "n": len(system_df),
                "latency": {
                    "mean": system_df["latency_seconds"].mean(),
                    "std": system_df["latency_seconds"].std(),
                    "median": system_df["latency_seconds"].median(),
                    "min": system_df["latency_seconds"].min(),
                    "max": system_df["latency_seconds"].max(),
                },
                "response_length": {
                    "mean": system_df["response_length"].mean(),
                    "std": system_df["response_length"].std(),
                },
            }

            # Cost if available
            if "cost_usd" in system_df.columns:
                stats_dict[system]["cost"] = {
                    "total": system_df["cost_usd"].sum(),
                    "mean": system_df["cost_usd"].mean(),
                    "std": system_df["cost_usd"].std(),
                }

            # Tool calls if available
            if "tool_calls" in system_df.columns:
                stats_dict[system]["tool_calls"] = {
                    "mean": system_df["tool_calls"].mean(),
                    "std": system_df["tool_calls"].std(),
                }

        return stats_dict

    def run_statistical_tests(self) -> Dict[str, Any]:
        """
        Run statistical significance tests.

        Tests:
        - Independent t-test for latency
        - Mann-Whitney U test (non-parametric)
        - Cohen's d (effect size)
        - Confidence intervals
        """
        agent_df = self.df_success[self.df_success["system"] == "agent"]
        rag_df = self.df_success[self.df_success["system"] == "rag"]

        tests = {}

        # Latency comparison
        if not agent_df.empty and not rag_df.empty:
            agent_latency = agent_df["latency_seconds"].values
            rag_latency = rag_df["latency_seconds"].values

            # T-test
            t_stat, t_pvalue = stats.ttest_ind(agent_latency, rag_latency)

            # Mann-Whitney U (non-parametric)
            u_stat, u_pvalue = stats.mannwhitneyu(agent_latency, rag_latency)

            # Cohen's d (effect size)
            cohens_d = self._compute_cohens_d(agent_latency, rag_latency)

            # 95% confidence intervals
            agent_ci = stats.t.interval(0.95, len(agent_latency)-1,
                                        loc=np.mean(agent_latency),
                                        scale=stats.sem(agent_latency))
            rag_ci = stats.t.interval(0.95, len(rag_latency)-1,
                                      loc=np.mean(rag_latency),
                                      scale=stats.sem(rag_latency))

            tests["latency"] = {
                "t_statistic": t_stat,
                "t_pvalue": t_pvalue,
                "significant": t_pvalue < 0.05,
                "mann_whitney_u": u_stat,
                "mann_whitney_pvalue": u_pvalue,
                "cohens_d": cohens_d,
                "effect_size": self._interpret_cohens_d(cohens_d),
                "agent_ci": agent_ci,
                "rag_ci": rag_ci,
                "agent_mean": np.mean(agent_latency),
                "rag_mean": np.mean(rag_latency),
                "difference": np.mean(agent_latency) - np.mean(rag_latency),
                "percent_difference": ((np.mean(agent_latency) - np.mean(rag_latency)) / np.mean(rag_latency)) * 100
            }

        # Cost comparison (if available)
        if "cost_usd" in agent_df.columns and "cost_usd" in rag_df.columns:
            agent_cost = agent_df["cost_usd"].values
            rag_cost = rag_df["cost_usd"].values

            t_stat, t_pvalue = stats.ttest_ind(agent_cost, rag_cost)
            cohens_d = self._compute_cohens_d(agent_cost, rag_cost)

            tests["cost"] = {
                "t_statistic": t_stat,
                "t_pvalue": t_pvalue,
                "significant": t_pvalue < 0.05,
                "cohens_d": cohens_d,
                "effect_size": self._interpret_cohens_d(cohens_d),
                "agent_mean": np.mean(agent_cost),
                "rag_mean": np.mean(rag_cost),
                "difference": np.mean(agent_cost) - np.mean(rag_cost),
                "percent_difference": ((np.mean(agent_cost) - np.mean(rag_cost)) / np.mean(rag_cost)) * 100
            }

        return tests

    def _compute_cohens_d(self, group1: np.ndarray, group2: np.ndarray) -> float:
        """Compute Cohen's d effect size."""
        n1, n2 = len(group1), len(group2)
        var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
        pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
        return (np.mean(group1) - np.mean(group2)) / pooled_std

    def _interpret_cohens_d(self, d: float) -> str:
        """Interpret Cohen's d effect size."""
        abs_d = abs(d)
        if abs_d < 0.2:
            return "negligible"
        elif abs_d < 0.5:
            return "small"
        elif abs_d < 0.8:
            return "medium"
        else:
            return "large"

    def generate_all_visualizations(self):
        """Generate all publication-quality visualizations."""
        self._plot_latency_comparison()
        self._plot_latency_distribution()
        self._plot_performance_by_task()
        self._plot_performance_by_stock()
        self._plot_success_rate()
        if "cost_usd" in self.df_success.columns:
            self._plot_cost_comparison()
        if "tool_calls" in self.df_success.columns:
            self._plot_complexity_comparison()

        print(f"  Generated {len(list(self.output_dir.glob('*.png')))} charts")

    def _plot_latency_comparison(self):
        """Plot latency comparison with statistical annotations."""
        fig, ax = plt.subplots(figsize=(10, 6))

        agent_df = self.df_success[self.df_success["system"] == "agent"]
        rag_df = self.df_success[self.df_success["system"] == "rag"]

        data = [agent_df["latency_seconds"].values, rag_df["latency_seconds"].values]
        labels = ["Agent", "RAG"]

        bp = ax.boxplot(data, labels=labels, patch_artist=True,
                       boxprops=dict(facecolor='lightblue', alpha=0.7),
                       medianprops=dict(color='red', linewidth=2))

        ax.set_ylabel("Latency (seconds)", fontsize=12, fontweight='bold')
        ax.set_title("Response Time Comparison: Agent vs RAG", fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)

        # Add statistical annotation
        if len(data[0]) > 0 and len(data[1]) > 0:
            _, p_value = stats.ttest_ind(data[0], data[1])
            if p_value < 0.001:
                sig_text = "p < 0.001***"
            elif p_value < 0.01:
                sig_text = f"p = {p_value:.3f}**"
            elif p_value < 0.05:
                sig_text = f"p = {p_value:.3f}*"
            else:
                sig_text = f"p = {p_value:.3f} (ns)"

            ax.text(0.5, 0.98, sig_text, transform=ax.transAxes,
                   ha='center', va='top', fontsize=10,
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        plt.tight_layout()
        plt.savefig(self.output_dir / "latency_comparison.png", dpi=300, bbox_inches='tight')
        plt.close()

    def _plot_latency_distribution(self):
        """Plot latency distributions."""
        fig, ax = plt.subplots(figsize=(10, 6))

        for system, color in [("agent", "blue"), ("rag", "orange")]:
            system_df = self.df_success[self.df_success["system"] == system]
            ax.hist(system_df["latency_seconds"], bins=20, alpha=0.6,
                   label=system.upper(), color=color, edgecolor='black')

        ax.set_xlabel("Latency (seconds)", fontsize=12, fontweight='bold')
        ax.set_ylabel("Frequency", fontsize=12, fontweight='bold')
        ax.set_title("Latency Distribution", fontsize=14, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(self.output_dir / "latency_distribution.png", dpi=300, bbox_inches='tight')
        plt.close()

    def _plot_performance_by_task(self):
        """Plot performance breakdown by task type."""
        fig, ax = plt.subplots(figsize=(12, 6))

        task_summary = self.df_success.groupby(["task_name", "system"])["latency_seconds"].mean().unstack()

        task_summary.plot(kind="bar", ax=ax, color=["blue", "orange"], alpha=0.7)

        ax.set_xlabel("Task Type", fontsize=12, fontweight='bold')
        ax.set_ylabel("Mean Latency (seconds)", fontsize=12, fontweight='bold')
        ax.set_title("Performance by Task Type", fontsize=14, fontweight='bold')
        ax.legend(["Agent", "RAG"], fontsize=10)
        ax.grid(True, alpha=0.3, axis='y')
        plt.xticks(rotation=45, ha='right')

        plt.tight_layout()
        plt.savefig(self.output_dir / "performance_by_task.png", dpi=300, bbox_inches='tight')
        plt.close()

    def _plot_performance_by_stock(self):
        """Plot performance by stock."""
        fig, ax = plt.subplots(figsize=(14, 6))

        stock_summary = self.df_success.groupby(["ticker", "system"])["latency_seconds"].mean().unstack()

        stock_summary.plot(kind="bar", ax=ax, color=["blue", "orange"], alpha=0.7)

        ax.set_xlabel("Stock Ticker", fontsize=12, fontweight='bold')
        ax.set_ylabel("Mean Latency (seconds)", fontsize=12, fontweight='bold')
        ax.set_title("Performance by Stock", fontsize=14, fontweight='bold')
        ax.legend(["Agent", "RAG"], fontsize=10)
        ax.grid(True, alpha=0.3, axis='y')
        plt.xticks(rotation=45, ha='right')

        plt.tight_layout()
        plt.savefig(self.output_dir / "performance_by_stock.png", dpi=300, bbox_inches='tight')
        plt.close()

    def _plot_success_rate(self):
        """Plot success rate comparison."""
        fig, ax = plt.subplots(figsize=(8, 6))

        success_rate = self.df.groupby("system")["success"].mean() * 100

        bars = ax.bar(["Agent", "RAG"], success_rate.values, color=["blue", "orange"], alpha=0.7)
        ax.set_ylabel("Success Rate (%)", fontsize=12, fontweight='bold')
        ax.set_title("System Reliability", fontsize=14, fontweight='bold')
        ax.set_ylim(0, 105)
        ax.grid(True, alpha=0.3, axis='y')

        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}%', ha='center', va='bottom', fontweight='bold')

        plt.tight_layout()
        plt.savefig(self.output_dir / "success_rate.png", dpi=300, bbox_inches='tight')
        plt.close()

    def _plot_cost_comparison(self):
        """Plot cost comparison."""
        fig, ax = plt.subplots(figsize=(10, 6))

        cost_data = []
        labels = []

        for system in ["agent", "rag"]:
            system_df = self.df_success[self.df_success["system"] == system]
            if "cost_usd" in system_df.columns:
                cost_data.append(system_df["cost_usd"].values)
                labels.append(system.upper())

        if cost_data:
            bp = ax.boxplot(cost_data, labels=labels, patch_artist=True,
                           boxprops=dict(facecolor='lightgreen', alpha=0.7))

            ax.set_ylabel("Cost (USD)", fontsize=12, fontweight='bold')
            ax.set_title("API Cost Comparison", fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)

            plt.tight_layout()
            plt.savefig(self.output_dir / "cost_comparison.png", dpi=300, bbox_inches='tight')
            plt.close()

    def _plot_complexity_comparison(self):
        """Plot reasoning complexity (tool calls)."""
        fig, ax = plt.subplots(figsize=(10, 6))

        agent_df = self.df_success[self.df_success["system"] == "agent"]
        if "tool_calls" in agent_df.columns:
            ax.hist(agent_df["tool_calls"], bins=20, alpha=0.7, color='blue', edgecolor='black')

            ax.set_xlabel("Number of Tool Calls", fontsize=12, fontweight='bold')
            ax.set_ylabel("Frequency", fontsize=12, fontweight='bold')
            ax.set_title("Agent Reasoning Complexity", fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)

            plt.tight_layout()
            plt.savefig(self.output_dir / "complexity_distribution.png", dpi=300, bbox_inches='tight')
            plt.close()

    def generate_report(self, desc_stats: Dict, stat_tests: Dict):
        """Generate comprehensive analysis report."""
        report_path = self.output_dir / "analysis_report.txt"

        with open(report_path, 'w') as f:
            f.write("="*80 + "\n")
            f.write("COMPREHENSIVE ANALYSIS REPORT\n")
            f.write("Agent vs RAG Comparison for Financial Analysis\n")
            f.write("="*80 + "\n\n")

            f.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Experiments: {len(self.df)}\n")
            f.write(f"Successful Experiments: {len(self.df_success)}\n\n")

            # Descriptive Statistics
            f.write("\n" + "-"*80 + "\n")
            f.write("1. DESCRIPTIVE STATISTICS\n")
            f.write("-"*80 + "\n\n")

            for system in ["agent", "rag"]:
                if system in desc_stats:
                    f.write(f"{system.upper()} System:\n")
                    stats = desc_stats[system]
                    f.write(f"  N = {stats['n']}\n")
                    f.write(f"  Latency: {stats['latency']['mean']:.3f}s (±{stats['latency']['std']:.3f}s)\n")
                    f.write(f"    Median: {stats['latency']['median']:.3f}s\n")
                    f.write(f"    Range: [{stats['latency']['min']:.3f}s, {stats['latency']['max']:.3f}s]\n")
                    f.write(f"  Response Length: {stats['response_length']['mean']:.0f} chars\n")

                    if "cost" in stats:
                        f.write(f"  Total Cost: ${stats['cost']['total']:.4f}\n")
                        f.write(f"  Mean Cost: ${stats['cost']['mean']:.4f}\n")

                    if "tool_calls" in stats:
                        f.write(f"  Avg Tool Calls: {stats['tool_calls']['mean']:.2f}\n")

                    f.write("\n")

            # Statistical Tests
            if stat_tests:
                f.write("\n" + "-"*80 + "\n")
                f.write("2. STATISTICAL SIGNIFICANCE TESTS\n")
                f.write("-"*80 + "\n\n")

                if "latency" in stat_tests:
                    lt = stat_tests["latency"]
                    f.write("Latency Comparison:\n")
                    f.write(f"  Agent Mean: {lt['agent_mean']:.3f}s (95% CI: [{lt['agent_ci'][0]:.3f}, {lt['agent_ci'][1]:.3f}])\n")
                    f.write(f"  RAG Mean: {lt['rag_mean']:.3f}s (95% CI: [{lt['rag_ci'][0]:.3f}, {lt['rag_ci'][1]:.3f}])\n")
                    f.write(f"  Difference: {lt['difference']:.3f}s ({lt['percent_difference']:.1f}%)\n\n")
                    f.write(f"  T-test: t = {lt['t_statistic']:.3f}, p = {lt['t_pvalue']:.4f}\n")
                    f.write(f"  Mann-Whitney U: U = {lt['mann_whitney_u']:.0f}, p = {lt['mann_whitney_pvalue']:.4f}\n")
                    f.write(f"  Cohen's d: {lt['cohens_d']:.3f} ({lt['effect_size']})\n")
                    f.write(f"  Significant: {'YES' if lt['significant'] else 'NO'} (α = 0.05)\n\n")

                if "cost" in stat_tests:
                    ct = stat_tests["cost"]
                    f.write("Cost Comparison:\n")
                    f.write(f"  Agent Mean: ${ct['agent_mean']:.4f}\n")
                    f.write(f"  RAG Mean: ${ct['rag_mean']:.4f}\n")
                    f.write(f"  Difference: ${ct['difference']:.4f} ({ct['percent_difference']:.1f}%)\n")
                    f.write(f"  T-test: t = {ct['t_statistic']:.3f}, p = {ct['t_pvalue']:.4f}\n")
                    f.write(f"  Cohen's d: {ct['cohens_d']:.3f} ({ct['effect_size']})\n")
                    f.write(f"  Significant: {'YES' if ct['significant'] else 'NO'}\n\n")

            # Conclusions
            f.write("\n" + "-"*80 + "\n")
            f.write("3. KEY FINDINGS\n")
            f.write("-"*80 + "\n\n")

            if "latency" in stat_tests:
                lt = stat_tests["latency"]
                faster_system = "Agent" if lt['agent_mean'] < lt['rag_mean'] else "RAG"
                f.write(f"• {faster_system} is faster by {abs(lt['percent_difference']):.1f}%\n")
                if lt['significant']:
                    f.write(f"• Difference is statistically significant (p < 0.05)\n")
                    f.write(f"• Effect size is {lt['effect_size']}\n")
                else:
                    f.write(f"• Difference is not statistically significant\n")

            f.write("\n")
            f.write("="*80 + "\n")

        print(f"  Report saved to {report_path}")


def main():
    """Run analysis on experiment results."""
    import argparse

    parser = argparse.ArgumentParser(description="Analyze experiment results")
    parser.add_argument("results_csv", help="Path to results CSV file")

    args = parser.parse_args()

    analyzer = ExperimentAnalyzer(args.results_csv)
    analyzer.run_full_analysis()

    print("\n✅ Analysis complete!")
    print(f"📊 View charts in: {analyzer.output_dir}")


if __name__ == "__main__":
    main()
