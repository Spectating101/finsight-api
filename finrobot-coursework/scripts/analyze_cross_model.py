#!/usr/bin/env python3
"""
Analyze cross-model validation results
Shows if Agent > RAG holds across different models
"""
import json
import os
import glob
import sys
sys.path.append('/home/user/finsight-api/finrobot-coursework')

from scripts.analyze_with_statistics import analytical_claims, data_regurgitation_penalty, extract_agent_analysis

def load_model_results(results_dir='scripts/cross_model_results'):
    """Load results for all models"""
    models = {}

    agent_files = glob.glob(f'{results_dir}/*_agent.json')
    for agent_file in agent_files:
        model_name = os.path.basename(agent_file).replace('_agent.json', '')
        rag_file = agent_file.replace('_agent.json', '_rag.json')

        if not os.path.exists(rag_file):
            continue

        with open(agent_file) as f:
            agent_results = json.load(f)
        with open(rag_file) as f:
            rag_results = json.load(f)

        models[model_name] = {
            'agent': agent_results,
            'rag': rag_results
        }

    return models

def calculate_scores(results, system_type):
    """Calculate analytical value scores"""
    scores = []
    for r in results:
        if 'error' in r:
            continue

        if system_type == 'agent':
            text = extract_agent_analysis(r.get('transcript', ''))
        else:
            text = r.get('analysis', '')

        score = analytical_claims(text) - data_regurgitation_penalty(text)
        scores.append(score)

    return scores

def main():
    models = load_model_results()

    if not models:
        print("ERROR: No cross-model results found.")
        print("\nRun cross-model validation first:")
        print("  python run_cross_model_validation.py --openai-key sk-xxx")
        return

    print("="*80)
    print("CROSS-MODEL VALIDATION RESULTS")
    print("="*80)
    print("")

    summary = []
    for model_name, results in models.items():
        agent_scores = calculate_scores(results['agent'], 'agent')
        rag_scores = calculate_scores(results['rag'], 'rag')

        agent_mean = sum(agent_scores) / len(agent_scores) if agent_scores else 0
        rag_mean = sum(rag_scores) / len(rag_scores) if rag_scores else 0

        summary.append({
            'model': model_name,
            'agent_mean': agent_mean,
            'rag_mean': rag_mean,
            'agent_wins': agent_mean > rag_mean,
            'advantage': agent_mean - rag_mean
        })

        print(f"Model: {model_name}")
        print(f"  Agent: {agent_mean:.2f} (n={len(agent_scores)})")
        print(f"  RAG:   {rag_mean:.2f} (n={len(rag_scores)})")
        print(f"  Agent advantage: {agent_mean - rag_mean:+.2f}")
        print(f"  Winner: {'AGENT ✓' if agent_mean > rag_mean else 'RAG'}")
        print("")

    print("="*80)
    print("SUMMARY")
    print("="*80)

    agent_wins = sum(1 for s in summary if s['agent_wins'])
    total_models = len(summary)

    print(f"\nAgent wins: {agent_wins}/{total_models} models ({100*agent_wins/total_models:.0f}%)")

    if agent_wins == total_models:
        print("\n✓ Agent advantage GENERALIZES across all models tested!")
        print("  → Result is model-independent")
    elif agent_wins > total_models / 2:
        print(f"\n✓ Agent advantage holds for MAJORITY of models ({agent_wins}/{total_models})")
        print("  → Result is likely robust")
    else:
        print(f"\n⚠ Agent advantage does NOT generalize ({agent_wins}/{total_models})")
        print("  → Result may be model-specific")

    print("\nAverage agent advantage across models:")
    avg_advantage = sum(s['advantage'] for s in summary) / len(summary)
    print(f"  {avg_advantage:+.2f} points")

    # Save summary
    with open('scripts/cross_model_results/SUMMARY.txt', 'w') as f:
        f.write(f"Cross-Model Validation Summary\n")
        f.write(f"="*60 + "\n\n")
        for s in summary:
            f.write(f"{s['model']}: Agent {s['agent_mean']:.2f} vs RAG {s['rag_mean']:.2f} ")
            f.write(f"(Δ={s['advantage']:+.2f}) {'✓' if s['agent_wins'] else ''}\n")
        f.write(f"\nAgent wins: {agent_wins}/{total_models} models\n")
        f.write(f"Average advantage: {avg_advantage:+.2f}\n")

    print("\n✓ Summary saved to scripts/cross_model_results/SUMMARY.txt")

if __name__ == '__main__':
    main()
