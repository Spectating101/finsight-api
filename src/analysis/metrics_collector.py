"""
Quality Metrics Collector
Automated quality scoring for analysis responses
"""

import re
import structlog
from typing import Dict, Any

logger = structlog.get_logger(__name__)


class QualityMetricsCollector:
    """Collects quality metrics for analysis responses"""

    def collect(self, response: str, task: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect comprehensive quality metrics for a response.

        Args:
            response: The analysis text
            task: Type of analysis task
            metadata: System metadata (latency, tool calls, etc.)

        Returns:
            Dictionary of quality metrics
        """
        return {
            "completeness_score": self._score_completeness(response, task),
            "specificity_score": self._score_specificity(response),
            "citation_density": self._calculate_citation_density(response),
            "reasoning_coherence": self._score_reasoning_coherence(response),
            "composite_quality": self._calculate_composite_quality(response, task),
            "response_length": len(response),
            "word_count": len(response.split()),
        }

    def _score_completeness(self, response: str, task: str) -> float:
        """
        Score how completely the response addresses the task.

        Returns: 0-100 score
        """
        required_aspects = {
            "prediction": ["price", "target", "timeframe", "rationale"],
            "risk_analysis": ["risk", "factor", "impact", "likelihood"],
            "opportunity": ["opportunity", "entry", "exit", "catalyst"]
        }

        aspects = required_aspects.get(task, [])
        if not aspects:
            return 100.0

        found_aspects = sum(
            1 for aspect in aspects
            if aspect.lower() in response.lower()
        )

        score = (found_aspects / len(aspects)) * 100
        return round(score, 1)

    def _score_specificity(self, response: str) -> float:
        """
        Score how specific the response is (uses numbers vs vague terms).

        Returns: 0-100 score
        """
        # Count specific numerical references
        number_pattern = r'\$?\d+\.?\d*[MBT%]?|\d+%|\d+\.\d+'
        numbers = len(re.findall(number_pattern, response))

        # Count vague terms (negative indicator)
        vague_terms = ["could", "might", "maybe", "possibly", "perhaps", "generally", "usually"]
        vague_count = sum(
            response.lower().count(term) for term in vague_terms
        )

        # Score based on specificity vs vagueness
        words = len(response.split())
        if words == 0:
            return 0.0

        specificity_ratio = (numbers * 10) / max(words, 1)
        vagueness_penalty = (vague_count * 5) / max(words, 1)

        score = min(100, max(0, (specificity_ratio - vagueness_penalty) * 100))
        return round(score, 1)

    def _calculate_citation_density(self, response: str) -> float:
        """
        Calculate citations per 100 words.

        Returns: Citation density (e.g., 12.5 = 12.5 citations per 100 words)
        """
        # Count data citations (numbers, metrics, specific values)
        citation_patterns = [
            r'\$\d+\.?\d*[MBT]',  # Dollar amounts
            r'\d+\.?\d*%',  # Percentages
            r'P/E of \d+',  # Ratios
            r'RSI of \d+',  # Technical indicators
            r'EPS of \$\d+',  # Earnings metrics
        ]

        total_citations = sum(
            len(re.findall(pattern, response))
            for pattern in citation_patterns
        )

        word_count = len(response.split())
        if word_count == 0:
            return 0.0

        density = (total_citations / word_count) * 100
        return round(density, 2)

    def _score_reasoning_coherence(self, response: str) -> float:
        """
        Score the logical flow and coherence of reasoning.

        Returns: 0-100 score
        """
        # Count reasoning connectors (positive indicator)
        connectors = ["because", "therefore", "thus", "since", "given that", "as a result", "consequently"]
        connector_count = sum(
            response.lower().count(term) for term in connectors
        )

        # Count structured elements (bullets, numbers, sections)
        structure_indicators = response.count("\n") + response.count(":") + response.count(".")

        words = len(response.split())
        if words == 0:
            return 0.0

        # Coherence score based on reasoning structure
        coherence_ratio = ((connector_count * 20) + (structure_indicators * 2)) / max(words, 1)
        score = min(100, coherence_ratio * 100)

        return round(score, 1)

    def _calculate_composite_quality(self, response: str, task: str) -> float:
        """
        Calculate weighted composite quality score.

        Returns: 0-100 overall quality score
        """
        completeness = self._score_completeness(response, task)
        specificity = self._score_specificity(response)
        coherence = self._score_reasoning_coherence(response)

        # Weighted average
        weights = {
            "completeness": 0.3,
            "specificity": 0.35,
            "coherence": 0.35
        }

        composite = (
            completeness * weights["completeness"] +
            specificity * weights["specificity"] +
            coherence * weights["coherence"]
        )

        return round(composite, 1)


def estimate_cost(
    system_type: str,
    prompt_tokens: int,
    completion_tokens: int,
    tool_calls: int = 0
) -> float:
    """
    Estimate cost of analysis request.

    Args:
        system_type: "rag", "hybrid", or "agent"
        prompt_tokens: Input token count
        completion_tokens: Output token count
        tool_calls: Number of tool calls made

    Returns:
        Estimated cost in USD
    """
    # LLM pricing (LLaMA-3.3-70B on Groq - example rates)
    input_cost_per_1k = 0.00059
    output_cost_per_1k = 0.00079

    llm_cost = (
        (prompt_tokens / 1000) * input_cost_per_1k +
        (completion_tokens / 1000) * output_cost_per_1k
    )

    # Tool call overhead (API calls, processing)
    tool_cost = tool_calls * 0.0005

    total_cost = llm_cost + tool_cost

    logger.info(
        "Cost estimated",
        system=system_type,
        llm_cost=llm_cost,
        tool_cost=tool_cost,
        total=total_cost
    )

    return round(total_cost, 6)
