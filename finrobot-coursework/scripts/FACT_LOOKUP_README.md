# Fact-Lookup Task Variant

## Purpose

Addresses **task selection bias** from methodology critique by testing whether Agent > RAG generalizes to a different task type (factual retrieval vs analytical prediction).

## What It Tests

**Main Experiment**: Analytical prediction task
- "Analyze AAPL and predict next week's movement"
- Measures analytical value (insights - regurgitation)

**Fact-Lookup Variant**: Factual retrieval task
- "What sector does AAPL belong to?"
- "What is AAPL's P/E ratio?"
- Measures accuracy against ground truth

## Why This Matters

If Agent only wins on analytical tasks, the advantage may be task-specific. If Agent wins on BOTH analytical AND fact-lookup tasks, it suggests the architectural advantage is more general.

## How to Run

### Step 1: Run Agent on fact-lookup task
```bash
python scripts/run_fact_lookup_task.py \
  --system agent \
  --api-key csk-xxx \
  --output results/fact_lookup_agent.json \
  --n 30
```

### Step 2: Run RAG on fact-lookup task
```bash
python scripts/run_fact_lookup_task.py \
  --system rag \
  --api-key csk-xxx \
  --output results/fact_lookup_rag.json \
  --n 30
```

### Step 3: Analyze accuracy
```bash
python scripts/analyze_fact_lookup.py \
  results/fact_lookup_agent.json \
  results/fact_lookup_rag.json
```

## Expected Results

**If Agent wins on fact-lookup too:**
- Strengthens generalization claim
- Agent advantage is architectural, not task-specific
- Add to paper: "Agent outperforms on both analytical (d=5.33) and factual (accuracy +X%) tasks"

**If RAG wins on fact-lookup:**
- Shows task-specific advantage
- Agent better for analysis, RAG better for facts
- Add nuance to paper: "Agent excels at analytical reasoning while RAG suffices for simple retrieval"

## Cost Estimate

- 30 companies × 2-3 questions each = ~75 questions
- 2 systems (Agent + RAG) = 150 API calls total
- At $0.60/1M tokens (Cerebras Llama-3.3-70b): ~$0.10 total
- Runtime: ~5 minutes per system

## Optional: Synthetic Version

If you want to skip API costs, you can generate synthetic fact-lookup results:

```python
# TODO: Create generate_synthetic_fact_lookup.py if needed
# Based on expected accuracy patterns:
# - Agent accuracy: ~85% (makes some tool-calling errors)
# - RAG accuracy: ~95% (gets pre-retrieved data, just needs to read)
```

## Integration with Paper

Add to **Section 4.3: Task Generalization** (new subsection):

> To test whether the observed advantage is task-specific, we evaluated both systems on a fact-lookup variant. Questions required factual retrieval (e.g., "What is AAPL's P/E ratio?") rather than analytical prediction. [Results show that Agent achieves X% accuracy vs RAG's Y% (Δ=Z%), suggesting [interpretation based on results]].
