#!/usr/bin/env python3
"""
Create publication-quality visualizations for FinRobot research paper
"""
import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

# Set publication quality parameters
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 10
plt.rcParams['font.family'] = 'serif'
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['xtick.labelsize'] = 9
plt.rcParams['ytick.labelsize'] = 9
plt.rcParams['legend.fontsize'] = 9
plt.rcParams['figure.titlesize'] = 13

def load_results():
    """Load experimental results"""
    with open('scripts/results_agent.json') as f:
        agent = json.load(f)
    with open('scripts/results_rag.json') as f:
        rag = json.load(f)
    with open('scripts/results_zeroshot.json') as f:
        zero = json.load(f)
    return agent, rag, zero

def create_analytical_value_comparison():
    """Figure 1: Analytical Value Comparison"""
    fig, ax = plt.subplots(figsize=(8, 5))

    systems = ['Agent\n(FinRobot)', 'RAG\n(Baseline)', 'Zero-shot\n(No Data)']
    analytical_claims = [25, 28, 6]
    regurgitation_penalty = [1, 18, 0]
    net_scores = [24, 10, 6]

    x = np.arange(len(systems))
    width = 0.25

    # Stacked bars showing claims and penalty
    bars1 = ax.bar(x - width, analytical_claims, width, label='Analytical Claims', color='#2ecc71', alpha=0.8)
    bars2 = ax.bar(x, [p * -1 for p in regurgitation_penalty], width, label='Data Regurgitation (penalty)', color='#e74c3c', alpha=0.8)
    bars3 = ax.bar(x + width, net_scores, width, label='Net Analytical Value', color='#3498db', alpha=0.9, edgecolor='black', linewidth=1.5)

    ax.set_ylabel('Score', fontweight='bold')
    ax.set_title('Analytical Value: Agent vs RAG vs Zero-shot', fontweight='bold', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(systems, fontweight='bold')
    ax.legend(loc='upper left', framealpha=0.9)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.8)

    # Add value labels on bars
    for bar in bars3:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                f'{int(height)}',
                ha='center', va='bottom', fontweight='bold', fontsize=11)

    plt.tight_layout()
    plt.savefig('figures/fig1_analytical_value.png', bbox_inches='tight')
    print("✓ Created: fig1_analytical_value.png")
    plt.close()

def create_performance_metrics():
    """Figure 2: Multi-dimensional Performance Comparison"""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 9))

    systems = ['Agent', 'RAG', 'Zero-shot']
    colors = ['#3498db', '#e67e22', '#95a5a6']

    # Success Rate
    success_rates = [100, 100, 100]
    ax1.bar(systems, success_rates, color=colors, alpha=0.7, edgecolor='black')
    ax1.set_ylabel('Success Rate (%)', fontweight='bold')
    ax1.set_title('(a) System Reliability', fontweight='bold')
    ax1.set_ylim([0, 110])
    ax1.grid(axis='y', alpha=0.3)
    for i, v in enumerate(success_rates):
        ax1.text(i, v + 2, f'{v}%', ha='center', fontweight='bold')

    # Latency
    latencies = [5.9, 4.1, 1.0]
    ax2.bar(systems, latencies, color=colors, alpha=0.7, edgecolor='black')
    ax2.set_ylabel('Average Latency (seconds)', fontweight='bold')
    ax2.set_title('(b) Response Time', fontweight='bold')
    ax2.grid(axis='y', alpha=0.3)
    for i, v in enumerate(latencies):
        ax2.text(i, v + 0.2, f'{v}s', ha='center', fontweight='bold')

    # Raw Facts vs Analytical Claims
    raw_facts = [88, 99, 10]
    analytical = [25, 28, 6]
    x = np.arange(len(systems))
    width = 0.35
    ax3.bar(x - width/2, raw_facts, width, label='Raw Facts', color='#95a5a6', alpha=0.7)
    ax3.bar(x + width/2, analytical, width, label='Analytical Claims', color='#2ecc71', alpha=0.7)
    ax3.set_ylabel('Count', fontweight='bold')
    ax3.set_title('(c) Content Analysis', fontweight='bold')
    ax3.set_xticks(x)
    ax3.set_xticklabels(systems)
    ax3.legend()
    ax3.grid(axis='y', alpha=0.3)

    # Net Analytical Value (main metric)
    net_scores = [24, 10, 6]
    bars = ax4.bar(systems, net_scores, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
    ax4.set_ylabel('Net Analytical Value', fontweight='bold')
    ax4.set_title('(d) Overall Quality Score', fontweight='bold')
    ax4.grid(axis='y', alpha=0.3)
    for i, v in enumerate(net_scores):
        ax4.text(i, v + 0.5, f'{v}', ha='center', fontweight='bold', fontsize=12)

    # Highlight best performer
    bars[0].set_edgecolor('#2ecc71')
    bars[0].set_linewidth(3)

    plt.suptitle('FinRobot Performance Metrics Comparison', fontsize=14, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig('figures/fig2_performance_metrics.png', bbox_inches='tight')
    print("✓ Created: fig2_performance_metrics.png")
    plt.close()

def create_efficiency_scatter():
    """Figure 3: Efficiency vs Quality Trade-off"""
    fig, ax = plt.subplots(figsize=(8, 6))

    # Data points: (latency, analytical_value)
    systems_data = {
        'Agent (FinRobot)': (5.9, 24, '#3498db', 300),
        'RAG (Baseline)': (4.1, 10, '#e67e22', 250),
        'Zero-shot (No Data)': (1.0, 6, '#95a5a6', 200)
    }

    for name, (latency, value, color, size) in systems_data.items():
        ax.scatter(latency, value, s=size, alpha=0.7, c=color, edgecolors='black', linewidth=2, label=name)
        ax.annotate(name.split('(')[0].strip(), (latency, value),
                   xytext=(10, 10), textcoords='offset points',
                   fontweight='bold', fontsize=10,
                   bbox=dict(boxstyle='round,pad=0.5', facecolor=color, alpha=0.3))

    ax.set_xlabel('Average Latency (seconds)', fontweight='bold')
    ax.set_ylabel('Net Analytical Value Score', fontweight='bold')
    ax.set_title('Quality vs Speed Trade-off Analysis', fontweight='bold', pad=15)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(loc='lower right', framealpha=0.9)

    # Add diagonal reference line (efficiency frontier)
    ax.plot([0, 7], [0, 28], 'k--', alpha=0.2, linewidth=1, label='Linear efficiency')

    plt.tight_layout()
    plt.savefig('figures/fig3_efficiency_tradeoff.png', bbox_inches='tight')
    print("✓ Created: fig3_efficiency_tradeoff.png")
    plt.close()

def create_architecture_comparison():
    """Figure 4: Conceptual Architecture Comparison"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Agent Architecture (Multi-step)
    ax1.text(0.5, 0.9, 'Agent Architecture', ha='center', fontsize=12, fontweight='bold')

    components = ['User Query', 'Planning', 'Tool Selection', 'Execution', 'Synthesis', 'Response']
    y_positions = np.linspace(0.75, 0.15, len(components))

    for i, (comp, y) in enumerate(zip(components, y_positions)):
        color = '#3498db' if i in [1, 2, 4] else '#ecf0f1'  # Highlight key steps
        rect = mpatches.FancyBboxPatch((0.2, y-0.04), 0.6, 0.08,
                                       boxstyle="round,pad=0.01",
                                       facecolor=color, edgecolor='black', linewidth=2)
        ax1.add_patch(rect)
        ax1.text(0.5, y, comp, ha='center', va='center', fontweight='bold', fontsize=10)

        if i < len(components) - 1:
            ax1.annotate('', xy=(0.5, y_positions[i+1]+0.04), xytext=(0.5, y-0.04),
                        arrowprops=dict(arrowstyle='->', lw=2, color='black'))

    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)
    ax1.axis('off')
    ax1.text(0.5, 0.05, '5-10 iterations, multi-tool reasoning', ha='center', fontsize=9, style='italic')

    # RAG Architecture (Single-step)
    ax2.text(0.5, 0.9, 'RAG Architecture', ha='center', fontsize=12, fontweight='bold')

    components_rag = ['User Query', 'Retrieval', 'Context Assembly', 'LLM Generation', 'Response']
    y_positions_rag = np.linspace(0.75, 0.25, len(components_rag))

    for i, (comp, y) in enumerate(zip(components_rag, y_positions_rag)):
        color = '#e67e22' if i == 1 else '#ecf0f1'  # Highlight retrieval
        rect = mpatches.FancyBboxPatch((0.2, y-0.04), 0.6, 0.08,
                                       boxstyle="round,pad=0.01",
                                       facecolor=color, edgecolor='black', linewidth=2)
        ax2.add_patch(rect)
        ax2.text(0.5, y, comp, ha='center', va='center', fontweight='bold', fontsize=10)

        if i < len(components_rag) - 1:
            ax2.annotate('', xy=(0.5, y_positions_rag[i+1]+0.04), xytext=(0.5, y-0.04),
                        arrowprops=dict(arrowstyle='->', lw=2, color='black'))

    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.axis('off')
    ax2.text(0.5, 0.15, 'Single-pass, retrieval-augmented', ha='center', fontsize=9, style='italic')

    plt.suptitle('Architectural Differences: Agent vs RAG', fontsize=13, fontweight='bold')
    plt.tight_layout()
    plt.savefig('figures/fig4_architecture_comparison.png', bbox_inches='tight')
    print("✓ Created: fig4_architecture_comparison.png")
    plt.close()

def main():
    # Create figures directory
    Path('figures').mkdir(exist_ok=True)

    print("Generating publication-quality figures...")
    print("=" * 50)

    create_analytical_value_comparison()
    create_performance_metrics()
    create_efficiency_scatter()
    create_architecture_comparison()

    print("=" * 50)
    print("✓ All figures created in figures/")
    print("\nFigures ready for inclusion in research paper:")
    print("  - fig1_analytical_value.png")
    print("  - fig2_performance_metrics.png")
    print("  - fig3_efficiency_tradeoff.png")
    print("  - fig4_architecture_comparison.png")

if __name__ == '__main__':
    main()
