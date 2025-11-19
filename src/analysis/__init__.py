"""
AI Analysis Engine for FinSight API
Implements RAG, Hybrid, and Agent systems for financial analysis
"""

from enum import Enum


class SystemType(str, Enum):
    """Analysis system types"""
    RAG = "rag"
    HYBRID = "hybrid"
    AGENT = "agent"


class AnalysisTask(str, Enum):
    """Types of analysis tasks"""
    PREDICTION = "prediction"
    RISK_ANALYSIS = "risk_analysis"
    OPPORTUNITY = "opportunity"


__all__ = [
    "SystemType",
    "AnalysisTask",
]
