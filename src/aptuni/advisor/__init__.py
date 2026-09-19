"""Plugin catalog, Recipes and the basic Plugin Advisor (PRD §12, §26–§30; ADR-0014)."""

from aptuni.advisor.catalog import Catalog, CatalogError, load_catalog
from aptuni.advisor.manifest import PluginManifest, Recipe
from aptuni.advisor.recommend import AdvisorError, Recommendation, SetupAnswers, recommend

__all__ = [
    "AdvisorError",
    "Catalog",
    "CatalogError",
    "PluginManifest",
    "Recipe",
    "Recommendation",
    "SetupAnswers",
    "load_catalog",
    "recommend",
]
