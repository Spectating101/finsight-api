#!/bin/bash
# FinRobot Comparison Study - Clean version for teammates
# Compares Agent vs RAG vs Zero-shot on financial analysis

set -e

cd "$(dirname "$0")/.."
source .venv/bin/activate 2>/dev/null || true

# Config
MODEL="${MODEL:-llama-3.3-70b}"
# Expanded to 30 companies for publication-quality sample size
TICKERS="${TICKERS:-AAPL MSFT GOOGL NVDA AMD JPM BAC WFC GS MS XOM CVX COP SLB OXY JNJ UNH PFE ABBV TMO TSLA WMT HD NKE MCD BA CAT GE UPS HON}"
TEMP="${TEMP:-0.2}"

echo "=============================================="
echo "  FinRobot Comparison Study (Publication)"
echo "  Model: $MODEL"
echo "  Companies: 30 (6 sectors × 5 each)"
echo "  Temperature: $TEMP"
echo "=============================================="
echo ""

# Clean old results
rm -f scripts/results_*.json scripts/comparison_*.csv scripts/comparison_*.txt

# 1. Agent (with yfinance only - same data source as RAG for fairness)
echo "1/3: Running AGENT (FinRobot with yfinance tools)..."
python scripts/run_agent_yfinance.py $TICKERS \
    --model "$MODEL" \
    --temperature $TEMP \
    --output scripts/results_agent.json

# CRITICAL: 90s cooldown to clear Cerebras queue
echo ""
echo "⏳ Waiting 90s for API queue cooldown..."
sleep 90

# 2. RAG
echo ""
echo "2/3: Running RAG (retrieval + single LLM call)..."
python scripts/run_rag.py $TICKERS \
    --model "$MODEL" \
    --temperature $TEMP \
    --output scripts/results_rag.json

# CRITICAL: 90s cooldown to clear Cerebras queue
echo ""
echo "⏳ Waiting 90s for API queue cooldown..."
sleep 90

# 3. Zero-shot
echo ""
echo "3/3: Running ZERO-SHOT (no data)..."
python scripts/run_zeroshot.py $TICKERS \
    --model "$MODEL" \
    --temperature $TEMP \
    --output scripts/results_zeroshot.json

# Analyze with statistics
echo ""
echo "Analyzing results with statistical testing..."
python scripts/analyze_with_statistics.py

echo ""
echo "=============================================="
echo "  ✓ DONE!"
echo "  View results: cat scripts/comparison_summary.txt"
echo "=============================================="

