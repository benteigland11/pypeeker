# pypeeker-cli

[![PyPI](https://img.shields.io/pypi/v/pypeeker-cli.svg)](https://pypi.org/project/pypeeker-cli/)
[![Powered by Cartograph](https://img.shields.io/badge/Powered%20by-Cartograph-orange?style=flat-square)](https://github.com/benteigland11/Cartograph)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![CI](https://github.com/benteigland11/pypeeker/actions/workflows/ci.yml/badge.svg)](https://github.com/benteigland11/pypeeker/actions/workflows/ci.yml)

**Agentic DX for Python.** *DX = developer experience: the tools, feedback,
and ergonomics that make working in a codebase feel good. Agentic DX is the
same idea, but for the AI agent doing the work instead of a human.* pypeeker
gives AI coding agents AST-level views of any Python codebase — API surfaces,
side-effect maps, import cycles, symbol locations — surfaced through MCP in
token-efficient structured answers. So your agent can navigate, reason about,
and refactor Python without reading whole files.

> **Read-only by design.** pypeeker never edits, renames, or rewrites your
> code. No `apply`, no `fix`, no auto-refactor surface. Every tool answers a
> question about the codebase; the agent acts on the answer. This is a hard
> boundary, not a roadmap gap.

---

## Cartograph Showcase

pypeeker-cli is a premier showcase for [Cartograph](https://github.com/benteigland11/Cartograph), a platform for reusable engineering.

Every core feature in pypeeker-cli, from AST parsing to graph cycle detection, is implemented as a standalone, validated Cartograph widget. This architecture ensures that pypeeker-cli is not just a tool, but a modular assembly of hardened building blocks that can be easily extended or repurposed.

---

## What the agent gets

Three MCP tools, designed to keep the agent's context budget tight:

### `audit(directory, kind=...)` — project-wide checks
- `kind="cycles"` — import cycles + a `cycle_hubs` ranking of the most-tangled files
- `kind="missing-imports"` — hallucinated or broken internal import paths
- `kind="interfaces"` — missing docstrings and type annotations

### `peek(path, mode=..., symbol=...)` — file or symbol inspection
- `mode="skeleton"` — file/package API surface with line ranges for targeted reads
- `mode="locate"` / `"ancestry"` — find a symbol's definition or class parents
- `mode="impact"` — bidirectional analysis of a function: outbound (what it depends on) and inbound (who calls it). Use `direction="in"|"out"` to scope, `depth=N` + `root` for transitive outbound

### `cli(command, args)` — escape hatch
Runs `pypeeker <command> <args>` and returns stdout. For flags the typed tools don't expose (`--include-deps`, custom `--ignore`, `--format json` on text-default tools).

---

## Real examples

All outputs below are real, captured against [`psf/requests`](https://github.com/psf/requests) (and a small synthetic project for the cycles example). Each example shows what the agent invokes over MCP and what comes back.

### `audit(kind="cycles")` — find import cycles

Detects runtime and `TYPE_CHECKING` import cycles, ranks the most-tangled files via cycle hubs.

> Agent invokes: `audit(directory=".", kind="cycles")`

```
# circular imports
3 cycles found

[hubs] files in 2+ cycles:
  hub.py  3

[1] runtime cycle:
  hub.py:1  → a
  a.py:1  → hub

[2] runtime cycle:
  hub.py:2  → b
  b.py:1  → hub

[3] runtime cycle:
  c.py:1  → hub
  hub.py:3  → c
```

The `cycle_hubs` ranking tells the agent which file to refactor first — `hub.py` shows up in all 3 cycles, so untangling it dissolves them all. (psf/requests itself reports `(none)` — clean codebase.)

### `audit(kind="missing-imports")` — catch hallucinated imports

Walks every import statement; reports the ones that don't resolve to a real file.

> Agent invokes: `audit(directory="requests/", kind="missing-imports")`

```
# missing imports
utils.py:78     winreg
help.py:19      chardet
cookies.py:20   dummy_threading
compat.py:60    simplejson
compat.py:67    simplejson
__init__.py:53  chardet
```

In requests these are intentional optional/conditional imports — but the same scan over an agent-edited codebase catches imports the agent invented and never actually installed.

### `audit(kind="interfaces")` — find docstring and type-hint gaps

Reports public symbols missing docstrings or annotations.

> Agent invokes: `audit(directory="requests/", kind="interfaces")`

```
total gaps: 233

utils.py:126  dict_to_sequence
    missing_type_hint: d
    missing_return_type
utils.py:135  super_len
    missing_docstring
    missing_type_hint: o
    missing_return_type
utils.py:206  get_netrc_auth
    missing_type_hint: url
    missing_type_hint: raise_errors
    missing_return_type
```

One pass over the project; agent gets a punch list of every gap with file, line, and exact missing piece.

### `peek(mode="skeleton")` — file or package API map

Strips function bodies; returns imports, signatures, docstrings, and the line range each symbol occupies.

> Agent invokes: `peek(path="requests/api.py", mode="skeleton")`

```python
from . import sessions

def request(method, url, **kwargs):  # L14-59
    """
    Constructs and sends a :class:`Request <Request>`.
    ...
    """
    ...

def get(url, params=None, **kwargs):  # L62-73
    ...

def post(url, data=None, json=None, **kwargs):  # L103-115
    ...
```

The agent now knows exactly which lines (`L14-59`) to `Read` if it needs the body of `request()`. No full-file scan to find one method.

### `peek(mode="locate")` — pinpoint a definition

AST-aware lookup: returns scope ranges, distinguishes definitions from substring matches.

> Agent invokes: `peek(path="requests/", mode="locate", symbol="Session")`

```
# locate: Session
sessions.py:356-818  class Session(SessionRedirectMixin)
```

Pass `mode="ancestry"` to also resolve parent classes:

```
# locate: Session
sessions.py:356-818  class Session(SessionRedirectMixin)
  ↳ sessions.py:107-353  class SessionRedirectMixin
```

### `peek(mode="impact")` — bidirectional analysis of a function

Default: **both directions in one call.** *Outbound* = what this function depends on (calls, writes, globals). *Inbound* = who calls this function across the project.

> Agent invokes: `peek(path="requests/sessions.py", mode="impact", symbol="Session.send", root="requests/")`

```
# impact: Session.send

## outbound (what this function reaches into)

  external calls:   16
    ValueError
    adapter.send
    dispatch_hook
    extract_cookies_to_jar
    history.insert
    history.pop
    isinstance
    kwargs.get
    kwargs.pop
    kwargs.setdefault
    next
    preferred_clock
    resolve_proxies
    self.get_adapter
    self.resolve_redirects
    timedelta
  external writes:  0
  globals modified: 0

## inbound (who calls this) — 4 match(es)

  requests/sessions.py:265
  requests/sessions.py:591
  requests/sessions.py:705
  requests/auth.py:276
```

Two refactor questions answered in one call:

- **Outbound:** `Session.send` depends on 16 external calls, mutates zero external state, touches zero globals. Pure dispatcher — agent can trust the body without reading it.
- **Inbound:** 4 callers across 2 files. If the agent changes `Session.send`'s contract, those are the 4 lines that might break.

Scope flags:
- `direction="out"` — only outbound (when you only care about what the function depends on).
- `direction="in"` — only inbound (when you only care about callers).
- `depth=N` (max 5) — transitive outbound. Walks the call graph N levels and aggregates writes, globals, and unresolved calls into one surface. **Static resolution only:** `self.X`, `Class.X`, and statically-imported names are followed; dynamic dispatch is reported as `unresolved`, not silently followed. Cycle-safe.

### `cli(command, args)` — escape hatch

Runs an arbitrary `pypeeker <command> <args>` and returns its stdout. Use when you need a flag the typed tools don't expose.

> Agent invokes: `cli(command="impact", args=["Session.send", "requests/sessions.py", "--depth", "2", "--root", "requests/"])`

Returns raw `pypeeker` stdout in a `{stdout, stderr, exit_code}` envelope. Prefer the typed tools when you can — they're easier for agents to reason about — and reach for `cli` when you need a one-off flag.

---

## The token math

Same task — find where requests handles redirect auth — measured against
actual agent tool output, including the `Read` tool's line-number prefixes.
Tokens counted with OpenAI's `o200k_base` tokenizer (used by GPT-4o, o1, o3, and GPT-5).

| Workflow                                                                    | Tokens    |
|-----------------------------------------------------------------------------|----------:|
| `Read sessions.py` (full file)                                              |     9,063 |
| **`skeleton sessions.py` + 2 targeted `Read` calls (L128-158, L282-300)**   | **3,218** |

The agent ends up reading only the two methods that actually matter, instead
of 833 lines hoping the relevant code is in there — and the skeleton's line
ranges (`# L128-158`) made the targeting possible.

For project-scale orientation, mapping the full `requests` package (18 files):

| Operation                                                                   | Tokens |
|-----------------------------------------------------------------------------|-------:|
| `Read` every `.py` file in `requests/`                                      | 59,901 |
| `skeleton requests/`                                                        | 19,508 |

The entire library API surface — every public class, signature, docstring, and
line range — in one call.

---

## Install

Two steps: install the package, then register it with your agent. The
package ships an MCP server (`pypeeker mcp`); your agent connects to that
server and gets the tools described above.

```bash
pip install pypeeker-cli
```

After install, register with whichever agent you use:

#### Gemini CLI
Install as a native extension:
```bash
gemini extensions install https://github.com/benteigland11/pypeeker
```

#### Claude Code
Add as a persistent MCP server:
```bash
claude mcp add pypeeker-cli -- pypeeker mcp
```

#### Codex
Add as a global MCP server:
```bash
codex mcp add pypeeker-cli -- pypeeker mcp
```

#### Cursor and Roo Code
Pypeeker is pre-configured for automatic detection via `.cursor/mcp.json`.

#### Continue
The server is pre-configured via `.continue/mcpServers/pypeeker.json`.

#### Windsurf
The server is pre-configured via `.windsurf/mcp_config.json`.

#### Claude Desktop and Aider
Copy the JSON from `claude_desktop_snippet.json` into your global `claude_desktop_config.json`.

### Project config

Add a `[tool.pypeeker]` section to your `pyproject.toml` to extend the default
ignore list project-wide:

```toml
[tool.pypeeker]
ignore = ["legacy", "vendor"]
```

These directories are added to the defaults (`venv`, `__pycache__`, `dist`,
`node_modules`, `.mypy_cache`, `.tox`, `build`). Active skip list is returned
in every `audit` response under `meta.skip_list`.

### Update notifications

When the MCP server starts, it checks PyPI once per session (cached 24h, 2-second timeout, fail-quiet) for a newer release. If your installed version is stale, agents see a one-line `pip install -U pypeeker-cli` notice prepended to the server instructions; up-to-date sessions see nothing. Set `PYPEEKER_CLI_NO_VERSION_CHECK=1` to disable the check entirely (e.g. on airgapped networks).

---

## Reusable Core

Built using the following Cartograph Widgets (found in `cg/`):
- `cg-infra-agent-cli-python`: Machine-first declarative CLI framework.
- `data-ast-import-parser-python`: Root-aware static import analysis.
- `data-ast-skeleton-parser-python`: API signature extraction.
- `data-ast-symbol-locator-python`: Surgical symbol pinpointing and ancestry.
- `data-ast-interface-validator-python`: API gap detection.
- `data-ast-impact-analyzer-python`: Side-effect and dependency mapping.
- `infra-mcp-server-readiness-python`: FastMCP version stamping + CLI escape-hatch primitives.
- `infra-mcp-manifest-generator-python`: Automated distribution scaffolding.
- `universal-agent-response-python`: Standardized JSON schema.
- `universal-list-paginator-python`: Result set pagination.

---

## License

Licensed under the Apache License, Version 2.0. See the [LICENSE](LICENSE) file for details.
