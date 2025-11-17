#!/usr/bin/env python3
"""Quick test: Run one RAG and one Agent experiment to verify setup."""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.run_full_experiment import run_rag_experiment, run_agent_experiment

print("Testing RAG experiment on AAPL...")
rag_result = run_rag_experiment("AAPL", "prediction")
print(f"RAG Result: {rag_result['latency_total']}s latency")
print(f"Response preview: {rag_result['response'][:500]}...")

print("\n" + "="*50 + "\n")

print("Testing Agent experiment on AAPL...")
agent_result = run_agent_experiment("AAPL", "prediction")
print(f"Agent Result: {agent_result['latency_total']}s latency, {agent_result['tool_calls']} tool calls")
print(f"Response preview: {agent_result['response'][:500]}...")

print("\n\nTest complete!")
