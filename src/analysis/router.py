"""
Intelligent Router - Tier-based system selection
Routes analysis requests to optimal system based on user subscription tier
"""

import structlog
from typing import Optional
from groq import Groq

from src.models.user import User, PricingTier
from src.analysis import SystemType
from src.analysis.rag_system import RAGSystem
from src.analysis.hybrid_system import HybridSystem
from src.analysis.agent_system import AgentSystem
from src.analysis.rag_cache import RAGCache

logger = structlog.get_logger(__name__)


class IntelligentRouter:
    """
    Routes analysis requests to the appropriate system based on user tier.

    Tier → System Mapping:
    - FREE: No AI analysis (only basic metrics)
    - STARTER: RAG system (fast, cheap, basic quality)
    - PROFESSIONAL: Hybrid system (optimal balance) ⭐ RECOMMENDED
    - ENTERPRISE: Agent system (comprehensive, premium quality)
    """

    def __init__(
        self,
        rag_cache: RAGCache,
        llm_client: Groq,
        data_sources: dict
    ):
        # Initialize all systems
        self.rag_system = RAGSystem(rag_cache, llm_client)
        self.hybrid_system = HybridSystem(rag_cache, llm_client, data_sources)
        self.agent_system = AgentSystem(llm_client, data_sources)

        logger.info("Intelligent router initialized", systems=["rag", "hybrid", "agent"])

    def route_request(
        self,
        user: User,
        task: str,
        requested_system: Optional[str] = None
    ) -> SystemType:
        """
        Route analysis request to appropriate system.

        Args:
            user: User making the request
            task: Analysis task type
            requested_system: Optional explicit system request (if tier allows)

        Returns:
            SystemType enum indicating which system to use
        """

        # Tier-based routing (default)
        tier_routing = {
            PricingTier.STARTER: SystemType.RAG,
            PricingTier.PROFESSIONAL: SystemType.HYBRID,
            PricingTier.ENTERPRISE: SystemType.AGENT,
        }

        default_system = tier_routing.get(user.tier, SystemType.RAG)

        # If user explicitly requested a system, check if tier allows it
        if requested_system:
            requested = SystemType(requested_system.lower())

            # Check if user's tier allows the requested system
            if self._tier_allows_system(user.tier, requested):
                logger.info(
                    "Using requested system",
                    user_id=user.user_id,
                    tier=user.tier,
                    requested=requested.value
                )
                return requested
            else:
                logger.warning(
                    "Requested system not available for tier",
                    user_id=user.user_id,
                    tier=user.tier,
                    requested=requested.value,
                    using=default_system.value
                )

        logger.info(
            "Routing to system",
            user_id=user.user_id,
            tier=user.tier,
            system=default_system.value
        )

        return default_system

    def _tier_allows_system(self, tier: PricingTier, system: SystemType) -> bool:
        """Check if tier has access to requested system"""

        tier_permissions = {
            PricingTier.FREE: [],  # No AI analysis
            PricingTier.STARTER: [SystemType.RAG],
            PricingTier.PROFESSIONAL: [SystemType.RAG, SystemType.HYBRID],
            PricingTier.ENTERPRISE: [SystemType.RAG, SystemType.HYBRID, SystemType.AGENT],
        }

        allowed_systems = tier_permissions.get(tier, [])
        return system in allowed_systems

    async def execute_analysis(
        self,
        system_type: SystemType,
        ticker: str,
        task: str,
        additional_context: Optional[str] = None
    ) -> dict:
        """
        Execute analysis using the specified system.

        Args:
            system_type: Which system to use
            ticker: Stock ticker
            task: Analysis task
            additional_context: Optional additional context

        Returns:
            Analysis result dictionary
        """

        try:
            if system_type == SystemType.RAG:
                result = await self.rag_system.analyze(ticker, task, additional_context)
            elif system_type == SystemType.HYBRID:
                result = await self.hybrid_system.analyze(ticker, task, additional_context)
            elif system_type == SystemType.AGENT:
                result = await self.agent_system.analyze(ticker, task, additional_context)
            else:
                raise ValueError(f"Unknown system type: {system_type}")

            return result

        except Exception as e:
            logger.error(
                "Analysis execution failed",
                system=system_type.value,
                ticker=ticker,
                error=str(e),
                exc_info=True
            )
            raise


def create_router(rag_cache: RAGCache, llm_client: Groq, data_sources: dict) -> IntelligentRouter:
    """Factory function to create configured router"""
    return IntelligentRouter(rag_cache, llm_client, data_sources)
