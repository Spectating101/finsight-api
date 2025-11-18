#!/usr/bin/env python3
"""
Analyze experimental results and generate visualizations for research paper.
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Configuration
RESULTS_DIR = "results"
OUTPUT_DIR = "results/figures"


def load_latest_results():
    """Load the most recent experiment results."""
    results_path = Path(RESULTS_DIR)

    # Find latest summary CSV
    csv_files = list(results_path.glob("summary_*.csv"))
    if not csv_files:
        raise FileNotFoundError("No summary CSV files found")

    latest_csv = max(csv_files, key=lambda p: p.stat().st_mtime)
    df = pd.read_csv(latest_csv)

    # Load corresponding JSON files
    timestamp = latest_csv.stem.replace("summary_", "")

    with open(results_path / f"rag_results_{timestamp}.json") as f:
        rag_data = json.load(f)

    with open(results_path / f"agent_results_{timestamp}.json") as f:
        agent_data = json.load(f)

    # Try to load hybrid results if available
    hybrid_path = results_path / f"hybrid_results_{timestamp}.json"
    hybrid_data = None
    if hybrid_path.exists():
        with open(hybrid_path) as f:
            hybrid_data = json.load(f)

    return df, rag_data, agent_data, hybrid_data


def create_latency_comparison(df):
    """Create bar chart comparing latency between systems."""
    fig, ax = plt.subplots(figsize=(12, 6))

    systems_in_data = df['system'].unique()
    has_hybrid = 'hybrid' in systems_in_data

    rag_data = df[df['system'] == 'rag'].groupby('task')['latency_total'].mean()
    agent_data = df[df['system'] == 'agent'].groupby('task')['latency_total'].mean()

    x = np.arange(len(rag_data))

    if has_hybrid:
        hybrid_data = df[df['system'] == 'hybrid'].groupby('task')['latency_total'].mean()
        width = 0.25
        bars1 = ax.bar(x - width, rag_data.values, width, label='RAG Baseline', color='#2ecc71', alpha=0.8)
        bars2 = ax.bar(x, hybrid_data.values, width, label='Hybrid', color='#f39c12', alpha=0.8)
        bars3 = ax.bar(x + width, agent_data.values, width, label='FinRobot Agent', color='#3498db', alpha=0.8)
    else:
        width = 0.35
        bars1 = ax.bar(x - width/2, rag_data.values, width, label='RAG Baseline', color='#2ecc71', alpha=0.8)
        bars2 = ax.bar(x + width/2, agent_data.values, width, label='FinRobot Agent', color='#3498db', alpha=0.8)

    ax.set_ylabel('Latency (seconds)', fontsize=12)
    ax.set_xlabel('Task Type', fontsize=12)
    title = '3-Way Latency Comparison' if has_hybrid else 'Response Latency: FinRobot Agent vs RAG Baseline'
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([t.replace('_', ' ').title() for t in rag_data.index])
    ax.legend()

    # Add value labels
    for bar in bars1:
        height = bar.get_height()
        ax.annotate(f'{height:.1f}s', xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=8)
    for bar in bars2:
        height = bar.get_height()
        ax.annotate(f'{height:.1f}s', xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=8)
    if has_hybrid:
        for bar in bars3:
            height = bar.get_height()
            ax.annotate(f'{height:.1f}s', xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=8)

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/latency_comparison.png', dpi=300, bbox_inches='tight')
    plt.savefig(f'{OUTPUT_DIR}/latency_comparison.pdf', bbox_inches='tight')
    plt.close()
    print("Created: latency_comparison.png")


def create_reasoning_depth_chart(df):
    """Create chart showing reasoning depth metrics."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    systems_in_data = df['system'].unique()
    has_hybrid = 'hybrid' in systems_in_data

    # Tool calls comparison
    rag_tools = df[df['system'] == 'rag']['tool_calls'].mean()
    agent_tools = df[df['system'] == 'agent']['tool_calls'].mean()

    if has_hybrid:
        hybrid_tools = df[df['system'] == 'hybrid']['tool_calls'].mean()
        systems = ['RAG Baseline', 'Hybrid', 'FinRobot Agent']
        tool_counts = [rag_tools, hybrid_tools, agent_tools]
        colors = ['#2ecc71', '#f39c12', '#3498db']
    else:
        systems = ['RAG Baseline', 'FinRobot Agent']
        tool_counts = [rag_tools, agent_tools]
        colors = ['#2ecc71', '#3498db']

    bars = ax1.bar(systems, tool_counts, color=colors, alpha=0.8)
    ax1.set_ylabel('Average Tool Calls', fontsize=12)
    ax1.set_title('Tool Usage Comparison', fontsize=14, fontweight='bold')

    for bar in bars:
        height = bar.get_height()
        ax1.annotate(f'{height:.1f}', xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=11)

    # Reasoning steps comparison
    rag_steps = df[df['system'] == 'rag']['reasoning_steps'].mean()
    agent_steps = df[df['system'] == 'agent']['reasoning_steps'].mean()

    if has_hybrid:
        hybrid_steps = df[df['system'] == 'hybrid']['reasoning_steps'].mean()
        step_counts = [rag_steps, hybrid_steps, agent_steps]
    else:
        step_counts = [rag_steps, agent_steps]

    bars = ax2.bar(systems, step_counts, color=colors, alpha=0.8)
    ax2.set_ylabel('Average Reasoning Steps', fontsize=12)
    ax2.set_title('Reasoning Depth Comparison', fontsize=14, fontweight='bold')

    for bar in bars:
        height = bar.get_height()
        ax2.annotate(f'{height:.1f}', xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=11)

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/reasoning_depth.png', dpi=300, bbox_inches='tight')
    plt.savefig(f'{OUTPUT_DIR}/reasoning_depth.pdf', bbox_inches='tight')
    plt.close()
    print("Created: reasoning_depth.png")


def create_response_quality_chart(df):
    """Create chart showing response length and token usage."""
    fig, ax = plt.subplots(figsize=(12, 6))

    # Group by system and task
    grouped = df.groupby(['system', 'task'])['response_length'].mean().unstack()

    x = np.arange(len(grouped.columns))
    width = 0.35

    bars1 = ax.bar(x - width/2, grouped.loc['rag'].values, width, label='RAG Baseline', color='#2ecc71', alpha=0.8)
    bars2 = ax.bar(x + width/2, grouped.loc['agent'].values, width, label='FinRobot Agent', color='#3498db', alpha=0.8)

    ax.set_ylabel('Response Length (characters)', fontsize=12)
    ax.set_xlabel('Task Type', fontsize=12)
    ax.set_title('Response Depth: Character Count by Task', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([t.replace('_', ' ').title() for t in grouped.columns])
    ax.legend()

    # Add value labels
    for bar in bars1:
        height = bar.get_height()
        ax.annotate(f'{int(height)}', xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=9)
    for bar in bars2:
        height = bar.get_height()
        ax.annotate(f'{int(height)}', xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/response_quality.png', dpi=300, bbox_inches='tight')
    plt.savefig(f'{OUTPUT_DIR}/response_quality.pdf', bbox_inches='tight')
    plt.close()
    print("Created: response_quality.png")


def create_sector_analysis(df):
    """Create sector-wise comparison."""
    fig, ax = plt.subplots(figsize=(14, 7))

    # Get latency by sector
    sector_data = df.groupby(['sector', 'system'])['latency_total'].mean().unstack()

    x = np.arange(len(sector_data.index))
    width = 0.35

    bars1 = ax.bar(x - width/2, sector_data['rag'].values, width, label='RAG Baseline', color='#2ecc71', alpha=0.8)
    bars2 = ax.bar(x + width/2, sector_data['agent'].values, width, label='FinRobot Agent', color='#3498db', alpha=0.8)

    ax.set_ylabel('Average Latency (seconds)', fontsize=12)
    ax.set_xlabel('Sector', fontsize=12)
    ax.set_title('Performance by Market Sector', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(sector_data.index, rotation=45, ha='right')
    ax.legend()

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/sector_analysis.png', dpi=300, bbox_inches='tight')
    plt.savefig(f'{OUTPUT_DIR}/sector_analysis.pdf', bbox_inches='tight')
    plt.close()
    print("Created: sector_analysis.png")


def create_tradeoff_scatter(df):
    """Create scatter plot showing latency vs response depth trade-off."""
    fig, ax = plt.subplots(figsize=(10, 8))

    rag_df = df[df['system'] == 'rag']
    agent_df = df[df['system'] == 'agent']

    ax.scatter(rag_df['latency_total'], rag_df['response_length'],
               s=100, alpha=0.7, label='RAG Baseline', color='#2ecc71', edgecolors='black', linewidth=0.5)
    ax.scatter(agent_df['latency_total'], agent_df['response_length'],
               s=100, alpha=0.7, label='FinRobot Agent', color='#3498db', edgecolors='black', linewidth=0.5)

    ax.set_xlabel('Latency (seconds)', fontsize=12)
    ax.set_ylabel('Response Length (characters)', fontsize=12)
    ax.set_title('Latency vs Response Depth Trade-off', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Add trend lines
    z_rag = np.polyfit(rag_df['latency_total'], rag_df['response_length'], 1)
    p_rag = np.poly1d(z_rag)
    z_agent = np.polyfit(agent_df['latency_total'], agent_df['response_length'], 1)
    p_agent = np.poly1d(z_agent)

    rag_x = np.linspace(rag_df['latency_total'].min(), rag_df['latency_total'].max(), 100)
    agent_x = np.linspace(agent_df['latency_total'].min(), agent_df['latency_total'].max(), 100)

    ax.plot(rag_x, p_rag(rag_x), '--', color='#27ae60', alpha=0.5, linewidth=2)
    ax.plot(agent_x, p_agent(agent_x), '--', color='#2980b9', alpha=0.5, linewidth=2)

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/tradeoff_scatter.png', dpi=300, bbox_inches='tight')
    plt.savefig(f'{OUTPUT_DIR}/tradeoff_scatter.pdf', bbox_inches='tight')
    plt.close()
    print("Created: tradeoff_scatter.png")


def create_quality_score_comparison(df):
    """Create radar chart showing multi-dimensional quality scores."""
    if 'composite_quality_score' not in df.columns:
        print("Skipping quality score comparison - no quality metrics in data")
        return

    systems_in_data = df['system'].unique()
    has_hybrid = 'hybrid' in systems_in_data

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Composite quality scores by task
    rag_quality = df[df['system'] == 'rag'].groupby('task')['composite_quality_score'].mean()
    agent_quality = df[df['system'] == 'agent'].groupby('task')['composite_quality_score'].mean()

    x = np.arange(len(rag_quality))

    if has_hybrid:
        hybrid_quality = df[df['system'] == 'hybrid'].groupby('task')['composite_quality_score'].mean()
        width = 0.25
        bars1 = ax1.bar(x - width, rag_quality.values, width, label='RAG Baseline', color='#2ecc71', alpha=0.8)
        bars2 = ax1.bar(x, hybrid_quality.values, width, label='Hybrid', color='#f39c12', alpha=0.8)
        bars3 = ax1.bar(x + width, agent_quality.values, width, label='FinRobot Agent', color='#3498db', alpha=0.8)
    else:
        width = 0.35
        bars1 = ax1.bar(x - width/2, rag_quality.values, width, label='RAG Baseline', color='#2ecc71', alpha=0.8)
        bars2 = ax1.bar(x + width/2, agent_quality.values, width, label='FinRobot Agent', color='#3498db', alpha=0.8)

    ax1.set_ylabel('Composite Quality Score (0-100)', fontsize=12)
    ax1.set_xlabel('Task Type', fontsize=12)
    ax1.set_title('Response Quality Score by Task', fontsize=14, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels([t.replace('_', ' ').title() for t in rag_quality.index])
    ax1.legend()
    ax1.set_ylim(0, 100)

    for bar in bars1:
        height = bar.get_height()
        ax1.annotate(f'{height:.1f}', xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=9)
    for bar in bars2:
        height = bar.get_height()
        ax1.annotate(f'{height:.1f}', xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=9)
    if has_hybrid:
        for bar in bars3:
            height = bar.get_height()
            ax1.annotate(f'{height:.1f}', xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=9)

    # Quality dimension breakdown
    quality_dims = ['completeness_score', 'specificity_score', 'financial_quality_score', 'reasoning_coherence']
    dim_labels = ['Completeness', 'Specificity', 'Financial\nQuality', 'Reasoning\nCoherence']

    rag_scores = [df[df['system'] == 'rag'][dim].mean() for dim in quality_dims]
    agent_scores = [df[df['system'] == 'agent'][dim].mean() for dim in quality_dims]

    x = np.arange(len(dim_labels))

    if has_hybrid:
        hybrid_scores = [df[df['system'] == 'hybrid'][dim].mean() for dim in quality_dims]
        width = 0.25
        bars1 = ax2.bar(x - width, rag_scores, width, label='RAG Baseline', color='#2ecc71', alpha=0.8)
        bars2 = ax2.bar(x, hybrid_scores, width, label='Hybrid', color='#f39c12', alpha=0.8)
        bars3 = ax2.bar(x + width, agent_scores, width, label='FinRobot Agent', color='#3498db', alpha=0.8)
    else:
        width = 0.35
        bars1 = ax2.bar(x - width/2, rag_scores, width, label='RAG Baseline', color='#2ecc71', alpha=0.8)
        bars2 = ax2.bar(x + width/2, agent_scores, width, label='FinRobot Agent', color='#3498db', alpha=0.8)

    ax2.set_ylabel('Score (0-100)', fontsize=12)
    ax2.set_title('Quality Dimension Breakdown', fontsize=14, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(dim_labels, fontsize=10)
    ax2.legend()
    ax2.set_ylim(0, 100)

    for bar in bars1:
        height = bar.get_height()
        ax2.annotate(f'{height:.1f}', xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=8)
    for bar in bars2:
        height = bar.get_height()
        ax2.annotate(f'{height:.1f}', xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=8)
    if has_hybrid:
        for bar in bars3:
            height = bar.get_height()
            ax2.annotate(f'{height:.1f}', xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=8)

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/quality_scores.png', dpi=300, bbox_inches='tight')
    plt.savefig(f'{OUTPUT_DIR}/quality_scores.pdf', bbox_inches='tight')
    plt.close()
    print("Created: quality_scores.png")


def create_cost_benefit_analysis(df):
    """Create cost-benefit analysis visualization."""
    if 'estimated_cost_usd' not in df.columns:
        print("Skipping cost-benefit analysis - no cost metrics in data")
        return

    systems_in_data = df['system'].unique()
    has_hybrid = 'hybrid' in systems_in_data

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Cost comparison
    rag_costs = df[df['system'] == 'rag']['estimated_cost_usd'].mean() * 1000  # Convert to millicents
    agent_costs = df[df['system'] == 'agent']['estimated_cost_usd'].mean() * 1000

    if has_hybrid:
        hybrid_costs = df[df['system'] == 'hybrid']['estimated_cost_usd'].mean() * 1000
        systems = ['RAG Baseline', 'Hybrid', 'FinRobot Agent']
        costs = [rag_costs, hybrid_costs, agent_costs]
        colors = ['#2ecc71', '#f39c12', '#3498db']
    else:
        systems = ['RAG Baseline', 'FinRobot Agent']
        costs = [rag_costs, agent_costs]
        colors = ['#2ecc71', '#3498db']

    bars = ax1.bar(systems, costs, color=colors, alpha=0.8)
    ax1.set_ylabel('Cost per Query ($0.001)', fontsize=12)
    ax1.set_title('Average Cost per Query', fontsize=14, fontweight='bold')

    for bar in bars:
        height = bar.get_height()
        ax1.annotate(f'${height/1000:.6f}', xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=10)

    # Quality per dollar (efficiency)
    rag_quality = df[df['system'] == 'rag']['composite_quality_score'].mean()
    agent_quality = df[df['system'] == 'agent']['composite_quality_score'].mean()

    rag_efficiency = rag_quality / (rag_costs / 1000) if rag_costs > 0 else 0
    agent_efficiency = agent_quality / (agent_costs / 1000) if agent_costs > 0 else 0

    if has_hybrid:
        hybrid_quality = df[df['system'] == 'hybrid']['composite_quality_score'].mean()
        hybrid_efficiency = hybrid_quality / (hybrid_costs / 1000) if hybrid_costs > 0 else 0
        efficiencies = [rag_efficiency, hybrid_efficiency, agent_efficiency]
    else:
        efficiencies = [rag_efficiency, agent_efficiency]

    bars = ax2.bar(systems, efficiencies, color=colors, alpha=0.8)
    ax2.set_ylabel('Quality Points per $0.001', fontsize=12)
    ax2.set_title('Cost Efficiency (Quality per Dollar)', fontsize=14, fontweight='bold')

    for bar in bars:
        height = bar.get_height()
        ax2.annotate(f'{height:.1f}', xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=10)

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/cost_benefit.png', dpi=300, bbox_inches='tight')
    plt.savefig(f'{OUTPUT_DIR}/cost_benefit.pdf', bbox_inches='tight')
    plt.close()
    print("Created: cost_benefit.png")


def create_latency_quality_tradeoff(df):
    """Create scatter plot showing latency vs quality trade-off."""
    if 'composite_quality_score' not in df.columns:
        print("Skipping latency-quality tradeoff - no quality metrics in data")
        return

    systems_in_data = df['system'].unique()
    has_hybrid = 'hybrid' in systems_in_data

    fig, ax = plt.subplots(figsize=(10, 8))

    rag_df = df[df['system'] == 'rag']
    agent_df = df[df['system'] == 'agent']

    ax.scatter(rag_df['latency_total'], rag_df['composite_quality_score'],
               s=120, alpha=0.7, label='RAG Baseline', color='#2ecc71', edgecolors='black', linewidth=0.5)
    ax.scatter(agent_df['latency_total'], agent_df['composite_quality_score'],
               s=120, alpha=0.7, label='FinRobot Agent', color='#3498db', edgecolors='black', linewidth=0.5)

    if has_hybrid:
        hybrid_df = df[df['system'] == 'hybrid']
        ax.scatter(hybrid_df['latency_total'], hybrid_df['composite_quality_score'],
                   s=120, alpha=0.7, label='Hybrid', color='#f39c12', edgecolors='black', linewidth=0.5)

    ax.set_xlabel('Latency (seconds)', fontsize=12)
    ax.set_ylabel('Composite Quality Score (0-100)', fontsize=12)
    title = '3-Way Latency vs Quality Trade-off' if has_hybrid else 'Latency vs Quality Trade-off: Agent vs RAG'
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.legend(loc='lower right')
    ax.grid(True, alpha=0.3)

    # Add annotations for means
    rag_mean_lat = rag_df['latency_total'].mean()
    rag_mean_qual = rag_df['composite_quality_score'].mean()
    agent_mean_lat = agent_df['latency_total'].mean()
    agent_mean_qual = agent_df['composite_quality_score'].mean()

    ax.axhline(y=rag_mean_qual, color='#27ae60', linestyle='--', alpha=0.5, linewidth=1)
    ax.axhline(y=agent_mean_qual, color='#2980b9', linestyle='--', alpha=0.5, linewidth=1)

    ax.annotate(f'RAG Mean: {rag_mean_qual:.1f}', xy=(0.05, rag_mean_qual),
                xycoords=('axes fraction', 'data'), fontsize=9, color='#27ae60')
    ax.annotate(f'Agent Mean: {agent_mean_qual:.1f}', xy=(0.05, agent_mean_qual),
                xycoords=('axes fraction', 'data'), fontsize=9, color='#2980b9')

    if has_hybrid:
        hybrid_mean_qual = hybrid_df['composite_quality_score'].mean()
        ax.axhline(y=hybrid_mean_qual, color='#e67e22', linestyle='--', alpha=0.5, linewidth=1)
        ax.annotate(f'Hybrid Mean: {hybrid_mean_qual:.1f}', xy=(0.05, hybrid_mean_qual),
                    xycoords=('axes fraction', 'data'), fontsize=9, color='#e67e22')

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/latency_quality_tradeoff.png', dpi=300, bbox_inches='tight')
    plt.savefig(f'{OUTPUT_DIR}/latency_quality_tradeoff.pdf', bbox_inches='tight')
    plt.close()
    print("Created: latency_quality_tradeoff.png")


def create_summary_table(df):
    """Create comprehensive summary statistics table."""
    systems_in_data = df['system'].unique()
    has_hybrid = 'hybrid' in systems_in_data

    base_metrics = [
        'Average Latency (s)',
        'Std Dev Latency (s)',
        'Min Latency (s)',
        'Max Latency (s)',
        'Average Tool Calls',
        'Average Reasoning Steps',
        'Average Response Length (chars)',
        'Average Completion Tokens',
        'Total Experiments'
    ]

    rag_base = [
        f"{df[df['system']=='rag']['latency_total'].mean():.2f}",
        f"{df[df['system']=='rag']['latency_total'].std():.2f}",
        f"{df[df['system']=='rag']['latency_total'].min():.2f}",
        f"{df[df['system']=='rag']['latency_total'].max():.2f}",
        f"{df[df['system']=='rag']['tool_calls'].mean():.1f}",
        f"{df[df['system']=='rag']['reasoning_steps'].mean():.1f}",
        f"{df[df['system']=='rag']['response_length'].mean():.0f}",
        f"{df[df['system']=='rag']['completion_tokens'].mean():.0f}",
        f"{len(df[df['system']=='rag'])}"
    ]

    agent_base = [
        f"{df[df['system']=='agent']['latency_total'].mean():.2f}",
        f"{df[df['system']=='agent']['latency_total'].std():.2f}",
        f"{df[df['system']=='agent']['latency_total'].min():.2f}",
        f"{df[df['system']=='agent']['latency_total'].max():.2f}",
        f"{df[df['system']=='agent']['tool_calls'].mean():.1f}",
        f"{df[df['system']=='agent']['reasoning_steps'].mean():.1f}",
        f"{df[df['system']=='agent']['response_length'].mean():.0f}",
        f"{df[df['system']=='agent']['completion_tokens'].mean():.0f}",
        f"{len(df[df['system']=='agent'])}"
    ]

    if has_hybrid:
        hybrid_base = [
            f"{df[df['system']=='hybrid']['latency_total'].mean():.2f}",
            f"{df[df['system']=='hybrid']['latency_total'].std():.2f}",
            f"{df[df['system']=='hybrid']['latency_total'].min():.2f}",
            f"{df[df['system']=='hybrid']['latency_total'].max():.2f}",
            f"{df[df['system']=='hybrid']['tool_calls'].mean():.1f}",
            f"{df[df['system']=='hybrid']['reasoning_steps'].mean():.1f}",
            f"{df[df['system']=='hybrid']['response_length'].mean():.0f}",
            f"{df[df['system']=='hybrid']['completion_tokens'].mean():.0f}",
            f"{len(df[df['system']=='hybrid'])}"
        ]

    # Add quality metrics if available
    if 'composite_quality_score' in df.columns:
        quality_metrics = [
            'Composite Quality Score',
            'Completeness Score',
            'Specificity Score',
            'Financial Quality Score',
            'Reasoning Coherence',
            'Citation Density (per 100 words)',
            'Factor Coverage',
            'Actionable Recommendations',
            'Estimated Cost (USD)'
        ]

        rag_quality = [
            f"{df[df['system']=='rag']['composite_quality_score'].mean():.1f}",
            f"{df[df['system']=='rag']['completeness_score'].mean():.1f}",
            f"{df[df['system']=='rag']['specificity_score'].mean():.1f}",
            f"{df[df['system']=='rag']['financial_quality_score'].mean():.1f}",
            f"{df[df['system']=='rag']['reasoning_coherence'].mean():.1f}",
            f"{df[df['system']=='rag']['citation_density'].mean():.2f}",
            f"{df[df['system']=='rag']['factor_coverage'].mean():.1f}",
            f"{df[df['system']=='rag']['actionable_recommendations'].mean():.1f}",
            f"${df[df['system']=='rag']['estimated_cost_usd'].sum():.6f}"
        ]

        agent_quality = [
            f"{df[df['system']=='agent']['composite_quality_score'].mean():.1f}",
            f"{df[df['system']=='agent']['completeness_score'].mean():.1f}",
            f"{df[df['system']=='agent']['specificity_score'].mean():.1f}",
            f"{df[df['system']=='agent']['financial_quality_score'].mean():.1f}",
            f"{df[df['system']=='agent']['reasoning_coherence'].mean():.1f}",
            f"{df[df['system']=='agent']['citation_density'].mean():.2f}",
            f"{df[df['system']=='agent']['factor_coverage'].mean():.1f}",
            f"{df[df['system']=='agent']['actionable_recommendations'].mean():.1f}",
            f"${df[df['system']=='agent']['estimated_cost_usd'].sum():.6f}"
        ]

        if has_hybrid:
            hybrid_quality = [
                f"{df[df['system']=='hybrid']['composite_quality_score'].mean():.1f}",
                f"{df[df['system']=='hybrid']['completeness_score'].mean():.1f}",
                f"{df[df['system']=='hybrid']['specificity_score'].mean():.1f}",
                f"{df[df['system']=='hybrid']['financial_quality_score'].mean():.1f}",
                f"{df[df['system']=='hybrid']['reasoning_coherence'].mean():.1f}",
                f"{df[df['system']=='hybrid']['citation_density'].mean():.2f}",
                f"{df[df['system']=='hybrid']['factor_coverage'].mean():.1f}",
                f"{df[df['system']=='hybrid']['actionable_recommendations'].mean():.1f}",
                f"${df[df['system']=='hybrid']['estimated_cost_usd'].sum():.6f}"
            ]

        base_metrics.extend(quality_metrics)
        rag_base.extend(rag_quality)
        agent_base.extend(agent_quality)
        if has_hybrid:
            hybrid_base.extend(hybrid_quality)

    if has_hybrid:
        summary = {
            'Metric': base_metrics,
            'RAG Baseline': rag_base,
            'Hybrid': hybrid_base,
            'FinRobot Agent': agent_base
        }
        caption = 'Comprehensive Performance and Quality Metrics: 3-Way Comparison'
    else:
        summary = {
            'Metric': base_metrics,
            'RAG Baseline': rag_base,
            'FinRobot Agent': agent_base
        }
        caption = 'Comprehensive Performance and Quality Metrics: FinRobot Agent vs RAG Baseline'

    summary_df = pd.DataFrame(summary)
    summary_df.to_csv(f'{OUTPUT_DIR}/summary_statistics.csv', index=False)

    # Also create LaTeX table for paper
    latex_table = summary_df.to_latex(index=False, caption=caption, label='tab:performance')
    with open(f'{OUTPUT_DIR}/summary_table.tex', 'w') as f:
        f.write(latex_table)

    print("Created: summary_statistics.csv and summary_table.tex")
    return summary_df


def main():
    """Generate all analysis and visualizations."""
    import os
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Loading experimental results...")
    df, rag_data, agent_data, hybrid_data = load_latest_results()

    has_hybrid = 'hybrid' in df['system'].unique()

    print(f"Loaded {len(df)} experiment results")
    print(f"RAG experiments: {len(df[df['system']=='rag'])}")
    if has_hybrid:
        print(f"Hybrid experiments: {len(df[df['system']=='hybrid'])}")
    print(f"Agent experiments: {len(df[df['system']=='agent'])}")
    print(f"Columns available: {', '.join(df.columns[:10])}...")

    print("\nGenerating visualizations...")
    create_latency_comparison(df)
    create_reasoning_depth_chart(df)
    create_response_quality_chart(df)
    create_sector_analysis(df)
    create_tradeoff_scatter(df)

    # New quality-focused visualizations
    print("\nGenerating quality metrics visualizations...")
    create_quality_score_comparison(df)
    create_cost_benefit_analysis(df)
    create_latency_quality_tradeoff(df)

    print("\nGenerating summary statistics...")
    summary_df = create_summary_table(df)
    print("\n" + "="*60)
    comparison_type = "3-WAY COMPARISON" if has_hybrid else "COMPREHENSIVE METRICS SUMMARY"
    print(comparison_type)
    print("="*60)
    print(summary_df.to_string(index=False))

    print(f"\n✅ Analysis complete! All figures saved to {OUTPUT_DIR}/")
    print(f"Total visualizations: 8")
    print(f"  - Performance: latency_comparison, reasoning_depth, response_quality, sector_analysis")
    print(f"  - Trade-offs: tradeoff_scatter, latency_quality_tradeoff")
    print(f"  - Quality: quality_scores, cost_benefit")
    print(f"  - Tables: summary_statistics.csv, summary_table.tex")


if __name__ == "__main__":
    main()
