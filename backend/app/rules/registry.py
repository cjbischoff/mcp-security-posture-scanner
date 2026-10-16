"""
Rule registry — imports all rule modules and provides a list of rule instances.
"""
from app.rules import Rule
from app.rules.mcp001_injection import MCP001InjectionRule
from app.rules.mcp002_unconstrained_schema import MCP002UnconstrainedSchemaRule
from app.rules.mcp003_missing_annotations import MCP003MissingAnnotationsRule
from app.rules.mcp004_read_write_pairing import MCP004ReadWritePairingRule
from app.rules.mcp005_unauthenticated import MCP005UnauthenticatedRule
from app.rules.mcp006_broad_resource_uri import MCP006BroadResourceUriRule
from app.rules.mcp007_description_anomaly import MCP007DescriptionAnomalyRule
from app.rules.mcp008_missing_schema import MCP008MissingSchemaRule
from app.rules.mcp009_resource_injection import MCP009ResourceInjectionRule
from app.rules.mcp010_drift import MCP010DriftRule

RULES: list[Rule] = [
    MCP001InjectionRule(),
    MCP002UnconstrainedSchemaRule(),
    MCP003MissingAnnotationsRule(),
    MCP004ReadWritePairingRule(),
    MCP005UnauthenticatedRule(),
    MCP006BroadResourceUriRule(),
    MCP007DescriptionAnomalyRule(),
    MCP008MissingSchemaRule(),
    MCP009ResourceInjectionRule(),
    MCP010DriftRule(),
]


def get_rule(rule_id: str) -> Rule | None:
    """Get a rule instance by its ID."""
    for rule in RULES:
        if rule.metadata.rule_id == rule_id:
            return rule
    return None
