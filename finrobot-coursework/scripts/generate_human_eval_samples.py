#!/usr/bin/env python3
"""
Generate human evaluation samples for blind rating
Selects 50 random outputs (25 Agent, 25 RAG) for human judges
"""
import json
import random
import os

random.seed(42)  # Reproducible

# Load results
with open('scripts/results_agent.json') as f:
    agent = json.load(f)
with open('scripts/results_rag.json') as f:
    rag = json.load(f)

# Select 25 random from each (out of 30)
agent_samples = random.sample(agent, min(25, len(agent)))
rag_samples = random.sample(rag, min(25, len(rag)))

# Anonymize and shuffle
samples = []
for i, r in enumerate(agent_samples):
    samples.append({
        'id': f'sample_{len(samples)+1:03d}',
        'ticker': r['ticker'],
        'system': 'SYSTEM_A',  # Anonymized
        'true_system': 'agent',
        'output': r.get('transcript', r.get('analysis', '')).split('Market_Analyst (to User_Proxy):')[-1].strip()
    })

for i, r in enumerate(rag_samples):
    samples.append({
        'id': f'sample_{len(samples)+1:03d}',
        'ticker': r['ticker'],
        'system': 'SYSTEM_B',  # Anonymized
        'true_system': 'rag',
        'output': r.get('analysis', '')
    })

# Shuffle to blind raters
random.shuffle(samples)

# Re-assign IDs after shuffle
for i, s in enumerate(samples):
    s['id'] = f'sample_{i+1:03d}'

# Create evaluation directory
os.makedirs('human_evaluation', exist_ok=True)

# Save samples for rating
with open('human_evaluation/samples_for_rating.json', 'w') as f:
    # Don't include true_system in rating file (blind)
    rating_samples = [
        {
            'id': s['id'],
            'ticker': s['ticker'],
            'system': s['system'],
            'output': s['output']
        }
        for s in samples
    ]
    json.dump(rating_samples, f, indent=2)

# Save ground truth separately (for later analysis)
with open('human_evaluation/samples_ground_truth.json', 'w') as f:
    json.dump(samples, f, indent=2)

# Create CSV for easy rating
with open('human_evaluation/rating_sheet.csv', 'w') as f:
    f.write('Sample_ID,Ticker,System,Quality_Score_(1-5),Comments\n')
    for s in samples:
        # Clean output for CSV (remove newlines)
        clean_output = s['output'].replace('\n', ' ').replace(',', ';')[:200] + '...'
        f.write(f'{s["id"]},{s["ticker"]},{s["system"]},,\n')

print(f"✓ Generated {len(samples)} samples for human evaluation")
print(f"  - 25 Agent outputs (labeled SYSTEM_A)")
print(f"  - 25 RAG outputs (labeled SYSTEM_B)")
print(f"  - Randomly shuffled and anonymized")
print(f"\nFiles created:")
print(f"  human_evaluation/samples_for_rating.json")
print(f"  human_evaluation/samples_ground_truth.json")
print(f"  human_evaluation/rating_sheet.csv")
print(f"\nNext: Have 3 evaluators rate each sample 1-5")
