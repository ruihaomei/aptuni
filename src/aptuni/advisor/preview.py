"""Render a Recommendation as the localized, human-readable preview required by PRD §27/§29."""

from __future__ import annotations

from aptuni.advisor.catalog import Catalog
from aptuni.advisor.recommend import Choice, Recommendation
from aptuni.i18n import t


def plugin_name(catalog: Catalog, plugin_id: str, locale: str) -> str:
    plugin = catalog.plugins.get(plugin_id)
    return t(plugin.name, locale) if plugin else plugin_id


def _items(catalog: Catalog, choices: tuple[Choice, ...], locale: str) -> list[str]:
    return [t("advisor.preview.item", locale, name=plugin_name(catalog, c.plugin_id, locale),
              plugin_id=c.plugin_id, reason=t(c.reason, locale)) for c in choices]


def render_preview(rec: Recommendation, catalog: Catalog, locale: str) -> list[str]:
    recipe = catalog.recipes[rec.recipe_id]
    lines = [t("advisor.preview.title", locale), "",
             t("advisor.preview.recipe", locale, name=t(recipe.name, locale), recipe_id=recipe.id,
               goal=t(recipe.goal, locale))]
    if rec.requested_recipe_id != rec.recipe_id and rec.requested_recipe_id in catalog.recipes:
        wanted = catalog.recipes[rec.requested_recipe_id]
        lines.append(t("advisor.preview.requested", locale, name=t(wanted.name, locale), recipe_id=wanted.id))
    lines += ["", t("advisor.preview.selected", locale), *_items(catalog, rec.selected, locale)]
    if rec.deferred:
        lines += [t("advisor.preview.deferred", locale), *_items(catalog, rec.deferred, locale)]
    lines.append("")
    if rec.required_api_keys:
        lines.append(t("advisor.preview.api_keys_required", locale,
                       keys=", ".join(k.env for k in rec.required_api_keys)))
    else:
        lines.append(t("advisor.preview.api_keys_none", locale))
    if rec.optional_api_keys:
        lines.append(t("advisor.preview.api_keys_optional", locale,
                       keys=", ".join(f"{k.env} ({t(k.purpose, locale)})" for k in rec.optional_api_keys)))
    lines.append(t("advisor.preview.setup_minutes", locale, low=rec.setup_minutes[0], high=rec.setup_minutes[1]))
    lines.append(t("advisor.preview.docker", locale,
                   value=t("advisor.preview.yes" if rec.docker else "advisor.preview.no", locale)))
    lines.append(t("advisor.preview.difficulty", locale, value=t(f"advisor.difficulty.{rec.difficulty}", locale)))
    if rec.retention:
        kinds = ", ".join(t(f"advisor.retention.{kind}", locale) for kind in rec.retention)
        lines.append(t("advisor.preview.retention", locale, kinds=kinds))
    lines.append(t("advisor.preview.privacy", locale))
    lines += [t(f"advisor.preview.egress.{kind}", locale) for kind in rec.egress]
    if rec.host_file_access:
        lines.append(t("advisor.preview.host_file_access", locale))
    if not rec.egress and not rec.host_file_access:
        lines.append(t("advisor.preview.egress_none", locale))
    if rec.network:
        lines.append(t("advisor.preview.network", locale, origins=", ".join(rec.network)))
    lines.append(t(f"advisor.preview.host_release.{rec.host_release}", locale))
    lines += ["", t("advisor.preview.strengths", locale),
              *(t("advisor.preview.bullet", locale, text=t(key, locale)) for key in rec.strengths),
              t("advisor.preview.weaknesses", locale),
              *(t("advisor.preview.minus", locale, text=t(key, locale)) for key in rec.weaknesses)]
    if rec.notes:
        lines += ["", t("advisor.preview.notes", locale),
                  *(t("advisor.preview.note", locale, text=t(key, locale)) for key in rec.notes)]
    lines += ["", t("advisor.preview.digest", locale, digest=rec.digest), t("advisor.preview.nothing_changed", locale)]
    return lines
