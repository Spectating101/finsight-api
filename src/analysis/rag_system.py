"""
RAG System - Single-pass analysis with pre-fetched context
Fast, cost-efficient baseline for Starter tier
"""

import time
import structlog
from typing import Dict, Any, Optional
from groq import Groq

from src.analysis.rag_cache import RAGCache
from src.analysis.metrics_collector import QualityMetricsCollector, estimate_cost

logger = structlog.get_logger(__name__)


class RAGSystem:
    """
    RAG (Retrieval-Augmented Generation) System

    Single-pass analysis with pre-fetched static context.
    Fast (6-8s), cheap ($0.0004/query), basic quality (~61/100).
    """

    def __init__(self, rag_cache: RAGCache, llm_client: Groq):
        self.rag_cache = rag_cache
        self.llm = llm_client
        self.metrics_collector = QualityMetricsCollector()

    async def analyze(
        self,
        ticker: str,
        task: str,
        additional_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run RAG analysis: fast single-pass with cached context.

        Args:
            ticker: Stock ticker symbol
            task: Analysis task (prediction, risk_analysis, opportunity)
            additional_context: Optional additional user-provided context

        Returns:
            Analysis result with metadata
        """
        start_time = time.time()
        logger.info("RAG analysis started", ticker=ticker, task=task)

        try:
            # Step 1: Fetch cached context (fast)
            context = await self.rag_cache.get_company_context(ticker)

            if not context:
                # Fallback if no cache available
                context = {
                    "company_name": ticker,
                    "description": "Financial data analysis for " + ticker
                }

            # Step 2: Build prompt with context
            prompt = self._build_prompt(ticker, task, context, additional_context)

            # Step 3: Single LLM call (no tools, no iteration)
            response = self.llm.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial analyst providing concise, data-driven analysis."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=500,
            )

            result_text = response.choices[0].message.content
            usage = response.usage

            # Calculate metrics
            latency = time.time() - start_time
            cost = estimate_cost(
                system_type="rag",
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                tool_calls=0
            )

            quality_metrics = self.metrics_collector.collect(result_text, task, {})

            logger.info(
                "RAG analysis completed",
                ticker=ticker,
                latency=latency,
                quality=quality_metrics["composite_quality"]
            )

            return {
                "analysis": result_text,
                "metadata": {
                    "system": "rag",
                    "ticker": ticker,
                    "task": task,
                    "latency": round(latency, 2),
                    "tool_calls": 0,
                    "reasoning_steps": 1,
                    "cache_hit": context is not None,
                    "cost_usd": cost,
                    "quality_score": quality_metrics["composite_quality"],
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                }
            }

        except Exception as e:
            logger.error("RAG analysis failed", ticker=ticker, error=str(e), exc_info=True)
            raise

    def _build_prompt(
        self,
        ticker: str,
        task: str,
        context: Dict,
        additional_context: Optional[str]
    ) -> str:
        """Build prompt for RAG analysis"""

        task_instructions = {
            "prediction": "Provide a 1-week price prediction with target price and key rationale.",
            "risk_analysis": "Identify the top 3 risk factors with impact assessment.",
            "opportunity": "Identify investment opportunities with entry/exit recommendations."
        }

        instruction = task_instructions.get(task, "Provide financial analysis.")

        prompt = f"""Analyze {ticker} - {context.get('company_name', ticker)}

**Company Context:**
- Sector: {context.get('sector', 'Unknown')}
- Description: {context.get('description', 'N/A')}
- Key Strengths: {', '.join(context.get('key_strengths', []))}
- Key Risks: {', '.join(context.get('key_risks', []))}

**Task:** {instruction}

"""

        if additional_context:
            prompt += f"\n**Additional Context:** {additional_context}\n"

        prompt += "\nProvide concise, specific analysis with data-driven reasoning."

        return prompt
