"""Progress and deferred-source lines for ``aptuni setup apply`` (Beta Day 0, 2026-09-29).

Reading many sources can take minutes, so every step and every source announces itself on stderr
while it runs. A source that could not be read is listed afterwards with a plain reason and the
exact command to retry it; setup itself has already finished.
"""

from __future__ import annotations

import sys
from typing import Any

from aptuni.cli.render import delimited_untrusted
from aptuni.cli.setup_apply import Progress
from aptuni.i18n import has_message, t

__all__ = ["failure_lines", "printer"]


def printer(locale: str) -> Progress:
    """Return a progress callback that prints localized lines to stderr immediately."""

    def emit(key: str, **fields: Any) -> None:
        if key == "setup.progress.step":
            fields = {**fields, "step": t(f"setup.progress.kind.{fields.pop('kind')}", locale)}
        elif "source" in fields:
            fields = {**fields, "source": delimited_untrusted(str(fields["source"]))}
        print(t(key, locale, **fields), file=sys.stderr, flush=True)

    return emit


def failure_lines(failures: dict[str, str], sources: list[Any], locale: str) -> list[str]:
    """Explain each deferred source: what it is, why it was not read, and how to retry."""
    if not failures:
        return []
    labels = {source.id: (source.roots[0] if source.roots else source.id) for source in sources}
    lines = ["", t("setup.apply.sources_later", locale)]
    for source_id, code in failures.items():
        key = f"setup.source_reason.{code}"
        reason = t(key, locale) if has_message(key, locale) else t("setup.source_reason.other", locale, code=code)
        lines.append(t("setup.apply.source_later_line", locale,
                       source=delimited_untrusted(str(labels.get(source_id, source_id))), reason=reason))
        lines.append(t("setup.apply.source_retry", locale, source_id=source_id))
    return lines
