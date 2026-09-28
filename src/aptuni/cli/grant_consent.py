"""The consent screen a person reads before approving a plugin grant (Beta finding P3).

Everything shown is derived from the real ``PluginGrantPlan``. Public API v1 has no capability that
writes Profile, Memory or sources directly, and ``PluginGrantManager.plan`` refuses any egress other
than ``none``, so those two lines state invariants rather than plugin claims.
"""

from __future__ import annotations

from aptuni.api.v1.grants import PluginGrant, PluginGrantPlan
from aptuni.cli.render import delimited_untrusted
from aptuni.i18n import t

__all__ = ["render_grant_consent", "render_grant_result", "render_plan_footer"]

READ_CAPABILITIES = ("context.read", "profile.read", "memory.read", "evidence.read", "memory.review.read")
PROPOSE_CAPABILITIES = ("memory.propose",)


def render_grant_consent(plan: PluginGrantPlan, locale: str, name: str | None = None) -> list[str]:
    granted = set(plan.capabilities)
    # Legacy manifests declare no required set; do not label everything they asked for as optional.
    optional = set(plan.capabilities) - set(plan.required_capabilities) if plan.required_capabilities else set()
    who = f"{plan.plugin_id} {plan.plugin_version}"
    title = t("consent.title", locale, name=delimited_untrusted(name), who=who) if name else \
        t("consent.title_id", locale, who=who)
    lines = [title, "", t("consent.read", locale)]
    for capability in READ_CAPABILITIES:
        if capability in granted:
            lines.append("  ✓ " + _label(capability, locale, capability in optional))
    lines += [t("consent.modules", locale)]
    lines += [f"  ✓ {t(f'consent.module.{module}', locale)}" for module in plan.modules]
    lines += ["", t("consent.propose", locale)]
    for capability in PROPOSE_CAPABILITIES:
        if capability in granted:
            lines.append("  ✓ " + _label(capability, locale, capability in optional))
            lines.append("    " + t(f"consent.detail.{capability}", locale))
        else:
            lines.append("  ✗ " + t(f"consent.withheld.{capability}", locale))
    grant_id = "grant-" + plan.action_id.removeprefix("act-")
    lines += [
        "", t("consent.write", locale), "  ✗ " + t("consent.write_none", locale),
        "", t("consent.egress", locale), "  ✗ " + t("consent.egress_none", locale),
        "", t("consent.no_code", locale),
        t("consent.revoke", locale, command=f"aptuni developer grant revoke {grant_id}"),
    ]
    if optional:
        lines.append(t("consent.narrow", locale, required=", ".join(plan.required_capabilities)))
    return lines


def render_plan_footer(plan: PluginGrantPlan, locale: str) -> list[str]:
    expires = plan.expires_at.strftime("%Y-%m-%d %H:%M UTC")
    return ["", t("consent.expires", locale, action_id=plan.action_id, expires=expires),
            t("consent.apply_hint", locale, command=f"aptuni developer grant apply {plan.action_id}")]


def render_grant_result(grant: PluginGrant, locale: str) -> list[str]:
    return [t("consent.approved", locale, grant_id=grant.grant_id),
            t("consent.revoke", locale, command=f"aptuni developer grant revoke {grant.grant_id}")]


def _label(capability: str, locale: str, optional: bool) -> str:
    label = t(f"consent.capability.{capability}", locale)
    return label + t("consent.optional_suffix", locale) if optional else label
