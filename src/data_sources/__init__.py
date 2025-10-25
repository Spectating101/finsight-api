"""Data source plugins for FinSight"""

from src.data_sources.base import (
    DataSourcePlugin,
    DataSourceType,
    DataSourceCapability,
    FinancialData,
    DataSourceRegistry,
    get_registry,
    register_source
)

__all__ = [
    "DataSourcePlugin",
    "DataSourceType",
    "DataSourceCapability",
    "FinancialData",
    "DataSourceRegistry",
    "get_registry",
    "register_source"
]
