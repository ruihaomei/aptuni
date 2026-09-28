# Review 79 — Beta agent-led setup re-review (remediation `bc39391`)

**Scope:** Review 78's blocking finding and notes. Independent reviewer.

- B1 resolved. The plan refuses `--plugin-manifest` in exactly the cases where no adapter step
  exists (`local_only`, or no Claude Code/Codex host); verified across five privacy/host
  combinations. "Nothing leaves this device" and "no host grant" can no longer appear next to a
  plugin grant, and the release section names the plugin's modules and the host operators. The
  guide offers the plugin only when cloud processing and an agent are chosen.
- N1, N2, N4 and N6 are fixed; the resume-reuse test covers N3.
- Non-blocking notes, addressed afterwards test-first: the release line now starts "In addition"
  and says the plugin's reads reach the model provider of any agent that runs it; `setup apply`
  refuses a `plugin_grant` step in a plan without an adapter step (`setup_plugin_without_host`);
  a plugin grant removed by discarding its crash-left preview is reported as rolled back.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**
