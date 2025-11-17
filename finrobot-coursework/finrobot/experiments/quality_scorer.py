#!/usr/bin/env python3
"""
Comprehensive Quality Scoring Module for Agent vs RAG Comparison.

Provides multi-dimensional quality assessment beyond basic latency metrics.
"""

import re
from typing import Dict, Any, List
from dataclasses import dataclass, asdict


@dataclass
class QualityMetrics:
    """Complete quality metrics for a single response."""

    # Completeness (0-100)
    completeness_score: float
    num_requested_aspects: int
    num_addressed_aspects: int

    # Specificity (0-100)
    specificity_score: float
    specific_numbers_count: int
    vague_statements_count: int
    citation_density: float  # citations per 100 words

    # Financial Analysis Quality (0-100)
    financial_quality_score: float
    factor_coverage: int  # number of distinct factors mentioned
    risk_factors_count: int
    opportunity_factors_count: int
    actionable_recommendations: int

    # Reasoning Quality (0-100)
    reasoning_coherence: float
    logical_flow_score: float
    evidence_based_claims: int
    unsupported_claims: int

    # Cost Metrics
    total_tokens: int
    estimated_cost_usd: float
    cost_per_insight: float

    # Consistency (requires multiple runs)
    response_variance: float  # 0-100, lower is more consistent


def calculate_completeness(response: str, task: str) -> Dict[str, Any]:
    """Calculate how completely the response addresses the requested task."""

    # Define required aspects per task
    required_aspects = {
        "prediction": ["positive factors", "risk factors", "price prediction", "reasoning"],
        "risk_analysis": ["top risks", "severity levels", "quantification", "mitigation strategies"],
        "opportunity": ["entry points", "targets", "stop-loss", "confidence levels", "timeframe"]
    }

    aspects = required_aspects.get(task, required_aspects["prediction"])
    num_requested = len(aspects)

    response_lower = response.lower()
    addressed = 0

    # Check for each aspect
    aspect_patterns = {
        "positive factors": r"(positive|strength|bull|upside|advantage)",
        "risk factors": r"(risk|danger|concern|threat|downside|bear)",
        "price prediction": r"(predict|forecast|expect|target|estimate).*(price|\$|\%)",
        "reasoning": r"(because|due to|based on|as|since|therefore)",
        "top risks": r"(risk|danger|concern|threat)",
        "severity levels": r"(high|medium|low|critical|severe)",
        "quantification": r"\d+\.?\d*%|\$\d+",
        "mitigation strategies": r"(mitigat|hedge|protect|diversif|stop.loss)",
        "entry points": r"(entry|buy|enter|accumulate)",
        "targets": r"(target|exit|sell|take.profit)",
        "stop-loss": r"(stop.loss|risk.management|cut.loss)",
        "confidence levels": r"(confidence|probability|likelihood).*\d+",
        "timeframe": r"(week|month|day|quarter|year|horizon)"
    }

    for aspect in aspects:
        if aspect in aspect_patterns:
            if re.search(aspect_patterns[aspect], response_lower):
                addressed += 1

    score = (addressed / num_requested) * 100 if num_requested > 0 else 0

    return {
        "completeness_score": round(score, 2),
        "num_requested_aspects": num_requested,
        "num_addressed_aspects": addressed
    }


def calculate_specificity(response: str) -> Dict[str, Any]:
    """Calculate how specific the response is with concrete data."""

    # Count specific numbers (prices, percentages, ratios)
    price_pattern = r"\$\d+(?:\.\d+)?"
    percent_pattern = r"\d+(?:\.\d+)?%"
    ratio_pattern = r"\d+(?:\.\d+)?x|\d+(?:\.\d+)?:\d+"
    number_pattern = r"\b\d+(?:\.\d+)?\b"

    prices = len(re.findall(price_pattern, response))
    percents = len(re.findall(percent_pattern, response))
    ratios = len(re.findall(ratio_pattern, response))

    # More sophisticated number counting (excluding common non-data numbers)
    all_numbers = re.findall(number_pattern, response)
    significant_numbers = sum(1 for n in all_numbers if float(n) > 0.5 and float(n) < 1000000)

    specific_count = prices + percents + ratios + (significant_numbers // 3)

    # Count vague statements
    vague_patterns = [
        r"somewhat", r"relatively", r"fairly", r"quite", r"rather",
        r"approximately", r"around", r"about", r"roughly", r"maybe",
        r"probably", r"possibly", r"might", r"could be", r"seems"
    ]

    vague_count = sum(len(re.findall(pattern, response.lower())) for pattern in vague_patterns)

    # Calculate citation density (specific numbers per 100 words)
    word_count = len(response.split())
    citation_density = (specific_count / word_count) * 100 if word_count > 0 else 0

    # Score: more specific numbers = higher score, more vague = lower
    raw_score = (specific_count * 10) - (vague_count * 5)
    specificity_score = max(0, min(100, raw_score))

    return {
        "specificity_score": round(specificity_score, 2),
        "specific_numbers_count": specific_count,
        "vague_statements_count": vague_count,
        "citation_density": round(citation_density, 2)
    }


def calculate_financial_quality(response: str) -> Dict[str, Any]:
    """Assess financial analysis quality."""

    # Factor coverage - distinct financial concepts mentioned
    financial_factors = [
        r"p/e|price.to.earnings|earnings.multiple",
        r"market.cap",
        r"revenue|sales",
        r"profit|margin|earnings",
        r"growth",
        r"volatility|beta|risk",
        r"dividend",
        r"debt|leverage",
        r"cash.flow",
        r"valuation",
        r"technical|rsi|macd|sma|moving.average",
        r"volume",
        r"momentum",
        r"support|resistance",
        r"sector|industry"
    ]

    response_lower = response.lower()
    factor_coverage = sum(1 for factor in financial_factors if re.search(factor, response_lower))

    # Risk factors mentioned
    risk_patterns = r"(risk|danger|concern|threat|downside|bear|negative|challenge)"
    risk_count = len(re.findall(risk_patterns, response_lower))

    # Opportunity factors
    opportunity_patterns = r"(opportunity|upside|potential|growth|positive|bull|catalyst)"
    opportunity_count = len(re.findall(opportunity_patterns, response_lower))

    # Actionable recommendations
    action_patterns = [
        r"(buy|sell|hold|accumulate|reduce)",
        r"(entry|exit|target|stop.loss)",
        r"(position.size|allocat)",
        r"(recommend|suggest|advise)"
    ]
    actionable = sum(1 for pattern in action_patterns if re.search(pattern, response_lower))

    # Calculate composite score
    base_score = (factor_coverage / len(financial_factors)) * 40  # Max 40 points
    balance_score = min(risk_count, opportunity_count) * 5  # Max 25 points (if 5 each)
    action_score = actionable * 8  # Max 32 points (if all 4)

    quality_score = min(100, base_score + balance_score + action_score)

    return {
        "financial_quality_score": round(quality_score, 2),
        "factor_coverage": factor_coverage,
        "risk_factors_count": risk_count,
        "opportunity_factors_count": opportunity_count,
        "actionable_recommendations": actionable
    }


def calculate_reasoning_quality(response: str) -> Dict[str, Any]:
    """Assess logical reasoning and evidence quality."""

    # Evidence-based claims (statements with supporting data)
    evidence_patterns = [
        r"(based on|according to|data shows|analysis indicates)",
        r"(due to|because|since|as|therefore|thus|hence)",
        r"(demonstrates|confirms|validates|supports)",
        r"\d+%.*?(indicates|suggests|shows|means)"
    ]

    evidence_count = sum(len(re.findall(pattern, response.lower())) for pattern in evidence_patterns)

    # Unsupported claims (strong statements without backing)
    unsupported_patterns = [
        r"(will|definitely|certainly|surely|undoubtedly)(?! based| due| because)",
        r"(always|never|guaranteed|certain)"
    ]

    unsupported_count = sum(len(re.findall(pattern, response.lower())) for pattern in unsupported_patterns)

    # Logical flow indicators
    flow_markers = [
        r"first|second|third|finally|lastly",
        r"however|although|nevertheless|despite",
        r"therefore|consequently|thus|hence",
        r"additionally|furthermore|moreover",
        r"in conclusion|to summarize|overall"
    ]

    flow_score = sum(1 for marker in flow_markers if re.search(marker, response.lower())) * 15
    flow_score = min(100, flow_score)

    # Overall reasoning coherence
    coherence = max(0, min(100, (evidence_count * 15) - (unsupported_count * 20) + flow_score / 2))

    return {
        "reasoning_coherence": round(coherence, 2),
        "logical_flow_score": round(flow_score, 2),
        "evidence_based_claims": evidence_count,
        "unsupported_claims": unsupported_count
    }


def calculate_cost_metrics(
    prompt_tokens: int,
    completion_tokens: int,
    model: str = "llama-3.3-70b"
) -> Dict[str, Any]:
    """Calculate cost efficiency metrics."""

    # Pricing per 1M tokens (Groq pricing as baseline)
    pricing = {
        "llama-3.3-70b": {"input": 0.59, "output": 0.79},
        "llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
        "llama-3.1-70b": {"input": 0.59, "output": 0.79},
        "gpt-4": {"input": 30.0, "output": 60.0},
        "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
        "claude-3-sonnet": {"input": 3.0, "output": 15.0}
    }

    model_pricing = pricing.get(model, pricing["llama-3.3-70b"])

    # Calculate cost
    input_cost = (prompt_tokens / 1_000_000) * model_pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * model_pricing["output"]
    total_cost = input_cost + output_cost

    # Cost per insight (assuming insights correlate with specific numbers and recommendations)
    total_tokens = prompt_tokens + completion_tokens
    cost_per_100_tokens = (total_cost / total_tokens) * 100 if total_tokens > 0 else 0

    return {
        "total_tokens": total_tokens,
        "estimated_cost_usd": round(total_cost, 6),
        "cost_per_insight": round(cost_per_100_tokens, 6)
    }


def calculate_consistency_score(responses: List[str]) -> float:
    """Calculate consistency across multiple runs (lower variance = more consistent)."""
    if len(responses) < 2:
        return 0.0

    # Compare key metrics across responses
    scores = []
    for response in responses:
        spec = calculate_specificity(response)
        scores.append(spec["specific_numbers_count"])

    # Calculate variance
    mean = sum(scores) / len(scores)
    variance = sum((x - mean) ** 2 for x in scores) / len(scores)

    # Convert to 0-100 scale (0 = highly consistent, 100 = highly variable)
    return min(100, variance * 10)


def score_response(
    response: str,
    task: str,
    prompt_tokens: int,
    completion_tokens: int,
    model: str = "llama-3.3-70b",
    multiple_runs: List[str] = None
) -> QualityMetrics:
    """Calculate all quality metrics for a response."""

    completeness = calculate_completeness(response, task)
    specificity = calculate_specificity(response)
    financial_quality = calculate_financial_quality(response)
    reasoning = calculate_reasoning_quality(response)
    costs = calculate_cost_metrics(prompt_tokens, completion_tokens, model)

    consistency = 0.0
    if multiple_runs:
        consistency = calculate_consistency_score(multiple_runs)

    return QualityMetrics(
        completeness_score=completeness["completeness_score"],
        num_requested_aspects=completeness["num_requested_aspects"],
        num_addressed_aspects=completeness["num_addressed_aspects"],
        specificity_score=specificity["specificity_score"],
        specific_numbers_count=specificity["specific_numbers_count"],
        vague_statements_count=specificity["vague_statements_count"],
        citation_density=specificity["citation_density"],
        financial_quality_score=financial_quality["financial_quality_score"],
        factor_coverage=financial_quality["factor_coverage"],
        risk_factors_count=financial_quality["risk_factors_count"],
        opportunity_factors_count=financial_quality["opportunity_factors_count"],
        actionable_recommendations=financial_quality["actionable_recommendations"],
        reasoning_coherence=reasoning["reasoning_coherence"],
        logical_flow_score=reasoning["logical_flow_score"],
        evidence_based_claims=reasoning["evidence_based_claims"],
        unsupported_claims=reasoning["unsupported_claims"],
        total_tokens=costs["total_tokens"],
        estimated_cost_usd=costs["estimated_cost_usd"],
        cost_per_insight=costs["cost_per_insight"],
        response_variance=consistency
    )


def quality_metrics_to_dict(metrics: QualityMetrics) -> Dict[str, Any]:
    """Convert quality metrics to dictionary."""
    return asdict(metrics)


def calculate_composite_quality_score(metrics: QualityMetrics) -> float:
    """Calculate single composite quality score (0-100)."""
    weights = {
        "completeness": 0.20,
        "specificity": 0.25,
        "financial_quality": 0.25,
        "reasoning": 0.20,
        "consistency": 0.10
    }

    # Invert consistency (lower variance = better)
    consistency_score = 100 - metrics.response_variance

    composite = (
        metrics.completeness_score * weights["completeness"] +
        metrics.specificity_score * weights["specificity"] +
        metrics.financial_quality_score * weights["financial_quality"] +
        metrics.reasoning_coherence * weights["reasoning"] +
        consistency_score * weights["consistency"]
    )

    return round(composite, 2)
