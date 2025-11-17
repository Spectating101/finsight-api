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

    return df, rag_data, agent_data


def create_latency_comparison(df):
    """Create bar chart comparing latency between systems."""
    fig, ax = plt.subplots(figsize=(10, 6))

    rag_data = df[df['system'] == 'rag'].groupby('task')['latency_total'].mean()
    agent_data = df[df['system'] == 'agent'].groupby('task')['latency_total'].mean()

    x = np.arange(len(rag_data))
    width = 0.35

    bars1 = ax.bar(x - width/2, rag_data.values, width, label='RAG Baseline', color='#2ecc71', alpha=0.8)
    bars2 = ax.bar(x + width/2, agent_data.values, width, label='FinRobot Agent', color='#3498db', alpha=0.8)

    ax.set_ylabel('Latency (seconds)', fontsize=12)
    ax.set_xlabel('Task Type', fontsize=12)
    ax.set_title('Response Latency: FinRobot Agent vs RAG Baseline', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([t.replace('_', ' ').title() for t in rag_data.index])
    ax.legend()

    # Add value labels
    for bar in bars1:
        height = bar.get_height()
        ax.annotate(f'{height:.1f}s', xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=9)
    for bar in bars2:
        height = bar.get_height()
        ax.annotate(f'{height:.1f}s', xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/latency_comparison.png', dpi=300, bbox_inches='tight')
    plt.savefig(f'{OUTPUT_DIR}/latency_comparison.pdf', bbox_inches='tight')
    plt.close()
    print("Created: latency_comparison.png")


def create_reasoning_depth_chart(df):
    """Create chart showing reasoning depth metrics."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Tool calls comparison
    rag_tools = df[df['system'] == 'rag']['tool_calls'].mean()
    agent_tools = df[df['system'] == 'agent']['tool_calls'].mean()

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


def create_summary_table(df):
    """Create comprehensive summary statistics table."""
    summary = {
        'Metric': [
            'Average Latency (s)',
            'Std Dev Latency (s)',
            'Min Latency (s)',
            'Max Latency (s)',
            'Average Tool Calls',
            'Average Reasoning Steps',
            'Average Response Length (chars)',
            'Average Completion Tokens',
            'Total Experiments'
        ],
        'RAG Baseline': [
            f"{df[df['system']=='rag']['latency_total'].mean():.2f}",
            f"{df[df['system']=='rag']['latency_total'].std():.2f}",
            f"{df[df['system']=='rag']['latency_total'].min():.2f}",
            f"{df[df['system']=='rag']['latency_total'].max():.2f}",
            f"{df[df['system']=='rag']['tool_calls'].mean():.1f}",
            f"{df[df['system']=='rag']['reasoning_steps'].mean():.1f}",
            f"{df[df['system']=='rag']['response_length'].mean():.0f}",
            f"{df[df['system']=='rag']['completion_tokens'].mean():.0f}",
            f"{len(df[df['system']=='rag'])}"
        ],
        'FinRobot Agent': [
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
    }

    summary_df = pd.DataFrame(summary)
    summary_df.to_csv(f'{OUTPUT_DIR}/summary_statistics.csv', index=False)

    # Also create LaTeX table for paper
    latex_table = summary_df.to_latex(index=False, caption='Comparative Performance Metrics: FinRobot Agent vs RAG Baseline', label='tab:performance')
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
    df, rag_data, agent_data = load_latest_results()

    print(f"Loaded {len(df)} experiment results")
    print(f"RAG experiments: {len(df[df['system']=='rag'])}")
    print(f"Agent experiments: {len(df[df['system']=='agent'])}")

    print("\nGenerating visualizations...")
    create_latency_comparison(df)
    create_reasoning_depth_chart(df)
    create_response_quality_chart(df)
    create_sector_analysis(df)
    create_tradeoff_scatter(df)

    print("\nGenerating summary statistics...")
    summary_df = create_summary_table(df)
    print("\n" + "="*60)
    print("SUMMARY STATISTICS TABLE")
    print("="*60)
    print(summary_df.to_string(index=False))

    print(f"\n✅ Analysis complete! All figures saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
