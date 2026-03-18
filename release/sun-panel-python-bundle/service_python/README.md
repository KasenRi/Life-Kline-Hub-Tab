# Sun-Panel Python Backend

Python rewrite of the Sun-Panel backend.

This directory is self-contained for runtime use:

- built-in config template in `assets/conf.example.ini`
- built-in language files in `assets/lang/`
- built-in version file in `assets/version`

The original Go backend can still be kept in the repository for behavior comparison, but the Python backend no longer needs Go files to start or generate config.

Common commands from the repo root:

```bash
pnpm install
pnpm run backend:python:build-runtime
pnpm run backend:python:run
```

Runtime-only commands:

```bash
cd service_python
uv run pytest -q tests/test_parity.py
```

Optional Go parity tests:

```bash
cd service_python
SUN_PANEL_ENABLE_GO_PARITY=1 uv run pytest -q tests/test_parity.py
```

Docker deployment:

```bash
docker compose -f docker-compose.python.yml up --build -d
```
