# Neural AI Agents — Claude Code Rules

## Start here

Read `specs/v1-platform-restructure.md` before making any changes. It contains every architecture decision and why it was made.

---

## Spec-first process

- Any new feature needs a spec file in `specs/` with status `approved` before code is written.
- Copy `specs/_template.md` to start a new spec.
- `specs/backlog/` holds drafted specs not yet scheduled — the product roadmap.
- When creating a plan in plan mode, use the spec format from `specs/_template.md` and save it to `specs/{slug}.md` in the repo as the first implementation step.
- Never start implementing until the spec status is `approved`.

---

## Architecture rules

- `commons/` holds **only** `commons/logger.py`. Everything else is agent-owned.
- Each agent lives entirely in `agents/{demoN}/` — no agent code outside its folder.
- Platform logic (agent list, config, health API) lives in `app/`.
- Memory backend lives in each agent's `agentic/memory_backend.py` — not in commons.

---

## Port conventions (defined in `config.yaml`)

| Layer | Range |
|-------|-------|
| Platform frontend | 5000 |
| Platform backend (`app/`) | 5001 |
| Agent frontends | 8001 – 8099 |
| Agent backends (FastAPI) | 3001 – 3099 |

Ports are declared in each agent's `metadata.yaml` (`api_port`, `frontend_port`).

---

## Naming conventions

- Agent folders are `demo1`, `demo2`, `demo3` — **never** named after their use case.
- Display names come from `metadata.yaml` (`name` field): Calvin, Arvo, Lance.
- The template folder is `demox_v1_0` (current template version 1.0). Future template versions live alongside as `demox_v2_0`, `demox_v3_0`, etc. Underscores keep the folder name a valid Python module path so `entry_point` works after a copy.

---

## demox_v1_0 — the agent template (and future versions)

- `demox_v1_0` is the v1.0 template. **Never modify it. Never start it.** Same rule for `demox_v2_0` and any future version.
- `demox_vN_M/metadata.yaml` has `status: template` — the scanner skips ANY agent whose status is `template`, regardless of folder name. Don't rely on a folder-name check; the test in `app/tests/test_scanner_template_skip.py` enforces this.
- Every agent's `metadata.yaml` carries `template_version: "X.Y"` recording which template version it inherits from. Set it when you copy the template; don't change it later.
- To add a new agent:
  1. `cp -r agents/demox_v1_0 agents/demoN` (or whichever template version you want to inherit)
  2. Update `metadata.yaml`: name, description, use_case, domain, api_port, frontend_port, set `status: stub`, set `entry_point: agents.demoN.apis.main:app`, keep `template_version`.
  3. Find-and-replace `agents.demox_v1_0.` → `agents.demoN.` in the new folder's Python imports.

---

## UI rules

- **Light theme only.** CSS variables in `frontend/src/index.css` are the source of truth — copy them into each agent's `index.css`.
- `wireframes/` is the design source of truth for all pages.
- Never introduce dark backgrounds or override the light theme variables.

---

## Agent frontends

- Each `agents/demoN/frontend/` is a **standalone Vite project** with its own `package.json`.
- Reference shared components via `@shared` alias → `../../frontend/src`.
- `VITE_API_URL` is written by `agents/demoN/main.py` before Vite starts — **never hardcode it**.
- Each agent's `main.py` also sets `VITE_AGENT_ID` to the folder name (e.g. `demo1`).

---

## app/ extension pattern

Adding a new platform feature:
1. Create `app/routers/{domain}.py` with an `APIRouter`
2. Create `app/services/{domain}_service.py` for business logic
3. Add schemas to `app/schemas/` if needed
4. Register in `app/main.py` — **one line**: `app.include_router({domain}.router, prefix="/api")`

---

## scripts/

- `run.sh` reads `config.yaml` for port ranges, scans `agents/*/metadata.yaml`, skips `status: template`, calls each agent's `main.py`.
- `run.sh` validates for port conflicts before launching anything.
- Log files go to `agents/{name}/logs/` — never to a root `logs/` folder.
