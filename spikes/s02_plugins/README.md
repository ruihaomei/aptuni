# S02 spike — disposable prototype

Gate 0 proof for entry-point plugin discovery, explicit activation, failure isolation, and approval
bound to the installed dependency closure. **Disposable**; never imported by production code.
Findings and the reproduce command: [docs/dev/spikes/S02-plugins.md](../../docs/dev/spikes/S02-plugins.md).

- `s02/fixtures.py`: fixture distributions and an offline PEP 427 wheel builder
- `s02/registry.py`: discovery, approval/closure fingerprinting, activation with isolation
- `s02/cli.py`: JSON CLI used by the tests inside disposable venvs
- `tests/test_plugins.py`: 12 acceptance tests
