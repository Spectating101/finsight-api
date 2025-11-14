#!/usr/bin/env python3
"""
Analyze human evaluation ratings
Calculates inter-rater agreement, correlation with automatic metric, system comparisons
"""
import json
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import cohen_kappa_score
import matplotlib.pyplot as plt

def load_ratings(rater_files):
    """Load ratings from multiple raters (CSV format)"""
    ratings = {}
    for rater_id, file_path in enumerate(rater_files):
        df = pd.read_csv(file_path)
        ratings[f'rater_{rater_id+1}'] = df.set_index('Sample_ID')['Quality_Score_(1-5)'].to_dict()
    return ratings

def calculate_inter_rater_agreement(ratings):
    """Calculate Cohen's kappa between all rater pairs"""
    raters = list(ratings.keys())
    sample_ids = list(ratings[raters[0]].keys())

    kappas = []
    for i in range(len(raters)):
        for j in range(i+1, len(raters)):
            r1_scores = [ratings[raters[i]][sid] for sid in sample_ids]
            r2_scores = [ratings[raters[j]][sid] for sid in sample_ids]
            kappa = cohen_kappa_score(r1_scores, r2_scores, weights='quadratic')
            kappas.append({
                'rater1': raters[i],
                'rater2': raters[j],
                'kappa': kappa
            })

    return kappas

def calculate_average_ratings(ratings):
    """Calculate mean rating per sample across all raters"""
    sample_ids = list(ratings[list(ratings.keys())[0]].keys())
    avg_ratings = {}

    for sid in sample_ids:
        scores = [ratings[rater][sid] for rater in ratings.keys()]
        avg_ratings[sid] = np.mean(scores)

    return avg_ratings

def compare_systems(avg_ratings, ground_truth_file):
    """Compare SYSTEM_A vs SYSTEM_B ratings"""
    with open(ground_truth_file) as f:
        ground_truth = json.load(f)

    system_a_ratings = []
    system_b_ratings = []

    for sample in ground_truth:
        rating = avg_ratings.get(sample['id'])
        if rating is None:
            continue

        if sample['true_system'] == 'agent':
            system_a_ratings.append(rating)
        else:
            system_b_ratings.append(rating)

    # Statistical test
    t_stat, p_value = stats.ttest_ind(system_a_ratings, system_b_ratings)
    cohens_d = (np.mean(system_a_ratings) - np.mean(system_b_ratings)) / \
               np.sqrt((np.std(system_a_ratings)**2 + np.std(system_b_ratings)**2) / 2)

    return {
        'system_a_mean': np.mean(system_a_ratings),
        'system_a_std': np.std(system_a_ratings),
        'system_b_mean': np.mean(system_b_ratings),
        'system_b_std': np.std(system_b_ratings),
        't_statistic': t_stat,
        'p_value': p_value,
        'cohens_d': cohens_d,
        'system_a_ratings': system_a_ratings,
        'system_b_ratings': system_b_ratings
    }

def correlate_with_automatic_metric(avg_ratings, ground_truth_file, results_dir='scripts'):
    """Correlate human ratings with automatic analytical value scores"""
    # Load automatic scores
    with open(f'{results_dir}/detailed_results.csv') as f:
        auto_df = pd.read_csv(f)

    with open(ground_truth_file) as f:
        ground_truth = json.load(f)

    human_scores = []
    auto_scores = []

    for sample in ground_truth:
        if sample['id'] not in avg_ratings:
            continue

        human_score = avg_ratings[sample['id']]

        # Find corresponding automatic score
        auto_row = auto_df[(auto_df['ticker'] == sample['ticker']) &
                           (auto_df['system'].str.lower() == sample['true_system'])]

        if len(auto_row) > 0:
            auto_score = auto_row.iloc[0]['analytical_score']
            human_scores.append(human_score)
            auto_scores.append(auto_score)

    # Calculate correlation
    pearson_r, pearson_p = stats.pearsonr(human_scores, auto_scores)
    spearman_r, spearman_p = stats.spearmanr(human_scores, auto_scores)

    return {
        'pearson_r': pearson_r,
        'pearson_p': pearson_p,
        'spearman_r': spearman_r,
        'spearman_p': spearman_p,
        'human_scores': human_scores,
        'auto_scores': auto_scores
    }

def generate_report(kappas, system_comparison, correlation):
    """Generate human evaluation report"""
    report = []
    report.append("="*80)
    report.append("HUMAN EVALUATION RESULTS")
    report.append("="*80)
    report.append("")

    # Inter-rater agreement
    report.append("INTER-RATER AGREEMENT (Cohen's Kappa):")
    report.append("-" * 40)
    avg_kappa = np.mean([k['kappa'] for k in kappas])
    for k in kappas:
        report.append(f"  {k['rater1']} vs {k['rater2']}: κ = {k['kappa']:.3f}")
    report.append(f"\n  Average Kappa: {avg_kappa:.3f}")

    if avg_kappa > 0.6:
        report.append("  → SUBSTANTIAL agreement (κ > 0.6)")
    elif avg_kappa > 0.4:
        report.append("  → MODERATE agreement (0.4 < κ < 0.6)")
    else:
        report.append("  → FAIR agreement (κ < 0.4)")
    report.append("")

    # System comparison
    report.append("SYSTEM COMPARISON (Human Ratings):")
    report.append("-" * 40)
    report.append(f"  Agent (SYSTEM_A): {system_comparison['system_a_mean']:.2f} ± {system_comparison['system_a_std']:.2f}")
    report.append(f"  RAG (SYSTEM_B):   {system_comparison['system_b_mean']:.2f} ± {system_comparison['system_b_std']:.2f}")
    report.append(f"\n  t-statistic: {system_comparison['t_statistic']:.3f}")
    report.append(f"  p-value:     {system_comparison['p_value']:.6f} {'***' if system_comparison['p_value'] < 0.001 else ''}")
    report.append(f"  Cohen's d:   {system_comparison['cohens_d']:.3f}")

    if system_comparison['p_value'] < 0.05:
        winner = "Agent" if system_comparison['system_a_mean'] > system_comparison['system_b_mean'] else "RAG"
        report.append(f"\n  → {winner} is SIGNIFICANTLY better (p < 0.05)")
    else:
        report.append("\n  → No significant difference")
    report.append("")

    # Correlation with automatic metric
    report.append("CORRELATION WITH AUTOMATIC METRIC:")
    report.append("-" * 40)
    report.append(f"  Pearson correlation:  r = {correlation['pearson_r']:.3f}, p = {correlation['pearson_p']:.6f}")
    report.append(f"  Spearman correlation: ρ = {correlation['spearman_r']:.3f}, p = {correlation['spearman_p']:.6f}")

    if abs(correlation['pearson_r']) > 0.7:
        report.append("\n  → STRONG correlation (automatic metric validated!)")
    elif abs(correlation['pearson_r']) > 0.5:
        report.append("\n  → MODERATE correlation (metric is decent)")
    else:
        report.append("\n  → WEAK correlation (metric needs improvement)")
    report.append("")

    report.append("="*80)

    return '\n'.join(report)

def create_visualizations(system_comparison, correlation):
    """Create visualization plots"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # System comparison boxplot
    data = [system_comparison['system_a_ratings'], system_comparison['system_b_ratings']]
    ax1.boxplot(data, labels=['Agent\n(SYSTEM_A)', 'RAG\n(SYSTEM_B)'])
    ax1.set_ylabel('Human Rating (1-5)', fontweight='bold')
    ax1.set_title('Human Evaluation: Agent vs RAG', fontweight='bold')
    ax1.grid(axis='y', alpha=0.3)

    # Correlation scatter plot
    ax2.scatter(correlation['auto_scores'], correlation['human_scores'], alpha=0.6, s=50)
    ax2.set_xlabel('Automatic Metric Score', fontweight='bold')
    ax2.set_ylabel('Human Rating (1-5)', fontweight='bold')
    ax2.set_title(f'Metric Validation (r={correlation["pearson_r"]:.2f})', fontweight='bold')

    # Add trendline
    z = np.polyfit(correlation['auto_scores'], correlation['human_scores'], 1)
    p = np.poly1d(z)
    ax2.plot(sorted(correlation['auto_scores']), p(sorted(correlation['auto_scores'])),
             "r--", alpha=0.5, linewidth=2)
    ax2.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig('human_evaluation/human_eval_results.png', dpi=300, bbox_inches='tight')
    print("✓ Saved visualization: human_evaluation/human_eval_results.png")

def main():
    """
    Usage: python analyze_human_ratings.py

    Expects CSV files in human_evaluation/:
      - rater1_ratings.csv
      - rater2_ratings.csv
      - rater3_ratings.csv
    """
    import sys

    # Check if rating files exist
    rater_files = [
        'human_evaluation/rater1_ratings.csv',
        'human_evaluation/rater2_ratings.csv',
        'human_evaluation/rater3_ratings.csv'
    ]

    missing = [f for f in rater_files if not os.path.exists(f)]
    if missing:
        print(f"ERROR: Missing rating files: {missing}")
        print("\nTo use this script:")
        print("1. Have 3 evaluators complete their ratings")
        print("2. Save as: rater1_ratings.csv, rater2_ratings.csv, rater3_ratings.csv")
        print("3. Place in human_evaluation/ directory")
        print("4. Run this script")
        return

    # Load ratings
    ratings = load_ratings(rater_files)

    # Calculate inter-rater agreement
    kappas = calculate_inter_rater_agreement(ratings)

    # Calculate average ratings
    avg_ratings = calculate_average_ratings(ratings)

    # Compare systems
    system_comparison = compare_systems(avg_ratings, 'human_evaluation/samples_ground_truth.json')

    # Correlate with automatic metric
    correlation = correlate_with_automatic_metric(avg_ratings, 'human_evaluation/samples_ground_truth.json')

    # Generate report
    report = generate_report(kappas, system_comparison, correlation)
    print(report)

    # Save report
    with open('human_evaluation/RESULTS.txt', 'w') as f:
        f.write(report)

    # Create visualizations
    create_visualizations(system_comparison, correlation)

    print("\n✓ Analysis complete!")
    print("  Results saved to: human_evaluation/RESULTS.txt")
    print("  Visualization: human_evaluation/human_eval_results.png")

if __name__ == '__main__':
    import os
    main()
