# Review 43 remediation — bind evaluation retention to one upload step

- **Responds to:** `43-m1-evaluation-harness-rereview.md`

The workflow checker now splits steps and requires one `actions/upload-artifact` step to contain the
exact evaluation path, the failure-safe `always()+hashFiles` condition and 14-day retention.
Regressions independently mutate the path and detach the condition onto a no-op step; both fail.
