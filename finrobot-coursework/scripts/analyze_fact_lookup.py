#!/usr/bin/env python3
"""
Analyze fact-lookup task results
Measures accuracy and compares Agent vs RAG on factual retrieval
"""
import json
import re
from typing import Dict, List

def extract_answer(response: str, question: str, ground_truth: Dict) -> Dict:
    """Extract answer from response and check against ground truth"""
    response_lower = response.lower()

    # Sector question
    if 'sector' in question.lower():
        gt_sector = ground_truth.get('sector', '').lower()
        if gt_sector in response_lower:
            return {'correct': True, 'type': 'sector', 'expected': gt_sector}
        else:
            return {'correct': False, 'type': 'sector', 'expected': gt_sector}

    # P/E ratio question
    if 'p/e' in question.lower() or 'pe ratio' in question.lower():
        gt_pe = ground_truth.get('pe_ratio')
        if gt_pe is None:
            return {'correct': None, 'type': 'pe_ratio', 'expected': 'N/A'}

        # Look for numbers in response
        numbers = re.findall(r'\d+\.?\d*', response)
        if numbers:
            for num_str in numbers:
                num = float(num_str)
                # Allow 10% tolerance
                if abs(num - gt_pe) / gt_pe < 0.1:
                    return {'correct': True, 'type': 'pe_ratio', 'expected': gt_pe}

        return {'correct': False, 'type': 'pe_ratio', 'expected': gt_pe}

    # Market cap question
    if 'market cap' in question.lower():
        gt_mcap = ground_truth.get('market_cap_billions')
        if gt_mcap is None:
            return {'correct': None, 'type': 'market_cap', 'expected': 'N/A'}

        # Look for numbers in billions
        numbers = re.findall(r'\d+\.?\d*', response)
        if numbers:
            for num_str in numbers:
                num = float(num_str)
                # Allow 10% tolerance
                if abs(num - gt_mcap) / gt_mcap < 0.1:
                    return {'correct': True, 'type': 'market_cap', 'expected': gt_mcap}

        return {'correct': False, 'type': 'market_cap', 'expected': gt_mcap}

    # 1-month return question
    if '1-month' in question.lower() or '1 month' in question.lower():
        gt_return = ground_truth.get('1mo_return_pct')
        if gt_return is None:
            return {'correct': None, 'type': '1mo_return', 'expected': 'N/A'}

        # Look for percentage numbers
        numbers = re.findall(r'-?\d+\.?\d*', response)
        if numbers:
            for num_str in numbers:
                num = float(num_str)
                # Allow 15% tolerance (returns can vary slightly)
                if abs(num - gt_return) < 1.5:
                    return {'correct': True, 'type': '1mo_return', 'expected': gt_return}

        return {'correct': False, 'type': '1mo_return', 'expected': gt_return}

    # Company name question
    if 'company name' in question.lower():
        gt_name = ground_truth.get('company_name', '').lower()
        # Check if any significant word from ground truth appears
        gt_words = set(gt_name.split())
        if any(word in response_lower for word in gt_words if len(word) > 3):
            return {'correct': True, 'type': 'company_name', 'expected': gt_name}
        else:
            return {'correct': False, 'type': 'company_name', 'expected': gt_name}

    return {'correct': None, 'type': 'unknown', 'expected': '?'}

def calculate_accuracy(results: List[Dict]) -> Dict:
    """Calculate accuracy metrics"""
    total_questions = 0
    correct = 0
    incorrect = 0
    unanswerable = 0

    by_type = {}

    for r in results:
        if 'error' in r:
            continue

        questions = r.get('questions', [])
        response = r.get('response', '')
        ground_truth = r.get('ground_truth', {})

        for question in questions:
            result = extract_answer(response, question, ground_truth)

            total_questions += 1
            if result['correct'] is True:
                correct += 1
            elif result['correct'] is False:
                incorrect += 1
            else:
                unanswerable += 1

            # Track by question type
            qtype = result['type']
            if qtype not in by_type:
                by_type[qtype] = {'correct': 0, 'incorrect': 0, 'total': 0}

            by_type[qtype]['total'] += 1
            if result['correct'] is True:
                by_type[qtype]['correct'] += 1
            elif result['correct'] is False:
                by_type[qtype]['incorrect'] += 1

    accuracy = correct / (correct + incorrect) if (correct + incorrect) > 0 else 0

    return {
        'total_questions': total_questions,
        'correct': correct,
        'incorrect': incorrect,
        'unanswerable': unanswerable,
        'accuracy': accuracy,
        'by_type': by_type
    }

def main():
    import sys
    if len(sys.argv) < 3:
        print("Usage: python analyze_fact_lookup.py <agent_results.json> <rag_results.json>")
        return

    agent_file = sys.argv[1]
    rag_file = sys.argv[2]

    with open(agent_file) as f:
        agent_results = json.load(f)

    with open(rag_file) as f:
        rag_results = json.load(f)

    print("="*80)
    print("FACT-LOOKUP TASK ANALYSIS")
    print("="*80)
    print("")

    # Agent accuracy
    print("AGENT SYSTEM:")
    agent_acc = calculate_accuracy(agent_results)
    print(f"  Total questions: {agent_acc['total_questions']}")
    print(f"  Correct: {agent_acc['correct']}")
    print(f"  Incorrect: {agent_acc['incorrect']}")
    print(f"  Unanswerable: {agent_acc['unanswerable']}")
    print(f"  Accuracy: {agent_acc['accuracy']*100:.1f}%")
    print("")

    print("  By question type:")
    for qtype, stats in agent_acc['by_type'].items():
        acc = stats['correct'] / stats['total'] if stats['total'] > 0 else 0
        print(f"    {qtype}: {acc*100:.1f}% ({stats['correct']}/{stats['total']})")
    print("")

    # RAG accuracy
    print("RAG SYSTEM:")
    rag_acc = calculate_accuracy(rag_results)
    print(f"  Total questions: {rag_acc['total_questions']}")
    print(f"  Correct: {rag_acc['correct']}")
    print(f"  Incorrect: {rag_acc['incorrect']}")
    print(f"  Unanswerable: {rag_acc['unanswerable']}")
    print(f"  Accuracy: {rag_acc['accuracy']*100:.1f}%")
    print("")

    print("  By question type:")
    for qtype, stats in rag_acc['by_type'].items():
        acc = stats['correct'] / stats['total'] if stats['total'] > 0 else 0
        print(f"    {qtype}: {acc*100:.1f}% ({stats['correct']}/{stats['total']})")
    print("")

    # Comparison
    print("="*80)
    print("COMPARISON")
    print("="*80)
    print("")

    diff = agent_acc['accuracy'] - rag_acc['accuracy']
    print(f"Accuracy difference: {diff*100:+.1f} percentage points")

    if agent_acc['accuracy'] > rag_acc['accuracy']:
        print(f"✓ Agent outperforms RAG on fact-lookup task")
        print(f"  → Agent advantage generalizes to factual retrieval")
    elif agent_acc['accuracy'] < rag_acc['accuracy']:
        print(f"✗ RAG outperforms Agent on fact-lookup task")
        print(f"  → Agent advantage may be specific to analytical tasks")
    else:
        print(f"≈ Agent and RAG perform similarly on fact-lookup task")
        print(f"  → Mixed evidence for task generalization")

    # Average latency
    agent_latencies = [r['latency_seconds'] for r in agent_results if 'latency_seconds' in r]
    rag_latencies = [r['latency_seconds'] for r in rag_results if 'latency_seconds' in r]

    if agent_latencies and rag_latencies:
        print(f"\nAverage latency:")
        print(f"  Agent: {sum(agent_latencies)/len(agent_latencies):.2f}s")
        print(f"  RAG: {sum(rag_latencies)/len(rag_latencies):.2f}s")

    # Save summary
    summary = {
        'agent_accuracy': agent_acc['accuracy'],
        'rag_accuracy': rag_acc['accuracy'],
        'difference': diff,
        'agent_wins': agent_acc['accuracy'] > rag_acc['accuracy']
    }

    with open('results/fact_lookup_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\n✓ Summary saved to results/fact_lookup_summary.json")

if __name__ == '__main__':
    main()
