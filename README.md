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

Three tools over MCP, designed to keep the agent's context budget tight:

### `audit(directory, kind=...)` — project-wide checks
- `kind="cycles"` — import cycles + a `cycle_hubs` ranking of the most-tangled files
- `kind="missing-imports"` — hallucinated or broken internal import paths
- `kind="interfaces"` — missing docstrings and type annotations

### `peek(path, mode=..., symbol=...)` — file or symbol inspection
- `mode="skeleton"` — file/package API surface with line ranges for targeted reads
- `mode="locate"` / `"ancestry"` — find a symbol's definition or class parents
- `mode="impact"` — both directions for a function: outbound (what it touches) + inbound (who calls it). Use `direction="in"|"out"` to scope, `depth=N` + `root` for transitive outbound

### `cli(command, args)` — escape hatch
Runs `pypeeker <command> <args>` and returns stdout. Use when you need a flag the consolidated tools don't expose (e.g., `--include-deps`, custom `--ignore`, `--format json` on a tool that defaults to text).

---

## Tool Showcase

Two views the `Read` tool can't give an agent in one call — both surfaced
through `peek`:

- **`mode="skeleton"`** — the API surface, without function bodies. Map a
  file or a whole package, get every signature with line ranges, jump
  straight to the methods that matter.
- **`mode="impact"`** — the side-effect map of a function, without mentally
  tracing the body. What it calls, what it reads, what it writes, whether
  it touches globals — answered structurally.

The walkthrough below uses [`psf/requests`](https://github.com/psf/requests) — a
real, well-known library — to answer a real agent question:
*"How does requests handle authentication during redirects?"*

### Map the file — `peek` with `mode="skeleton"`

The agent calls `peek` over MCP with skeleton mode. The tool strips every
function body and returns imports, signatures, docstrings, and the line
range each symbol occupies.

> Agent invokes: `peek(path="requests/sessions.py", mode="skeleton")`
> Returns:

```python
import os
import time
from .auth import _basic_auth_str
from .cookies import RequestsCookieJar, extract_cookies_to_jar
# ...

class SessionRedirectMixin:  # L107-353
    def get_redirect_target(self, resp):  # L108-126
        """Receives a Response. Returns a redirect URI or ``None``"""
        ...

    def should_strip_auth(self, old_url, new_url):  # L128-158
        """Decide whether Authorization header should be removed when redirecting"""
        ...

    def rebuild_auth(self, prepared_request, response):  # L282-300
        """When being redirected we may want to strip authentication..."""
        ...
```

The two methods we want — `should_strip_auth` and `rebuild_auth` — are now
visible with their exact line ranges.

### Trace what a function touches — `peek` with `mode="impact"`

Once the agent has found the function, the next question is usually *"what
does this affect?"* — globals, class state, external calls. Reading the body
to find out is the manual approach. `peek` in impact mode answers structurally:

> Agent invokes: `peek(path="requests/sessions.py", mode="impact", symbol="SessionRedirectMixin.rebuild_auth")`
> Returns:

```json
{
  "external": {
    "calls":  ["get_netrc_auth", "prepared_request.prepare_auth", "self.should_strip_auth"],
    "reads":  ["self.trust_env", "..."],
    "writes": [],
    "globals": []
  },
  "internal": {
    "writes": ["headers", "new_auth", "url"]
  }
}
```

Three external dependencies. Zero global writes. Zero shared-state mutation.
That's a refactor-safety check the agent can do *before* changing anything,
in one call instead of a multi-pass read.

Impact mode accepts both bare names (`rebuild_auth`) and qualified names
(`SessionRedirectMixin.rebuild_auth`) for unambiguous targeting when multiple
classes share method names.

#### `depth=N`: transitive blast radius across files

The harder refactor question is *"if I change this method's contract, what's
the cascade?"* — that's what its callees touch, and what their callees touch,
and so on. `depth=N` walks the call graph up to N levels (max 5), aggregates
every external write, global mutation, and reached symbol into one answer:

> Agent invokes: `peek(path="backend/services/chat_service.py", mode="impact", symbol="ChatService.process_message", depth=2, root=".")`
> Returns:

```
# impact: ChatService.process_message  (depth 2)

transitive surface across 32 reached symbols:
  external calls:   323 unique
  external writes:  1       <- danger zone for refactors
    self._failed_edit_hashes  in ChatService.process_message (depth 0)
  globals modified: 0

reached symbols:
  depth 0  ChatService.process_message     backend/services/chat_service.py
  depth 1  build_summary_context            backend/context_builder.py
  depth 1  schedule_summary_update          backend/summary_updater.py
  ... (29 more)

unresolved (notable, 63):
  print                          in ChatService.process_message [effect_builtin]
  asyncio.create_task            in ChatService.process_message [stdlib]
  re.search                      in ChatService.process_message [stdlib]
  hashlib.md5                    in ChatService.process_message [stdlib]
  json.dumps                     in ChatService.process_message [stdlib]
  ...

unresolved (filtered, 316): 265 dispatch, 48 pure builtin, 3 exception
```

A 2,805-line method that calls into 32 other functions transitively mutates
**exactly one** external attribute. That's a structural answer to "is this
safe to refactor?" — derived in one tool call, with the unresolved cases
flagged so the agent knows where its view is incomplete.

**Static resolution only.** `self.X`, `Class.X`, and statically-imported
names are followed. Dynamic dispatch (`obj.method()` where `obj`'s type is
inferred at runtime) is reported as `unresolved`, not silently followed.
Cycle-safe (visited-set deduplication). Project-bounded via the `root` parameter.

### The token math

Same task — find where requests handles redirect auth — measured against
actual agent tool output, including the `Read` tool's line-number prefixes.
Tokens counted with OpenAI's `o200k_base` tokenizer (used by GPT-4o, o1, o3, and GPT-5).

| Workflow                                                                    | Tokens |
|-----------------------------------------------------------------------------|-------:|
| `Read sessions.py` (full file)                                              | 9,063  |
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

### Also covered by the same tools

- **`peek(mode="locate"|"ancestry")`** — AST-aware symbol search with scope ranges. No false positives from substring matches; distinguishes definitions from inheritance.
- **`peek(mode="impact")`** — both directions of a function in one call: outbound (what it depends on) and inbound (who calls it). Replaces the prior `usages`-as-its-own-thing split.
- **`audit(kind="cycles")`** — import cycles, separates runtime cycles from safe `TYPE_CHECKING` cycles, ranks files by cycle membership.
- **`audit(kind="missing-imports")`** — hallucinated or broken internal imports.
- **`audit(kind="interfaces")`** — missing docstrings and type annotations across a project.

All modes default to condensed text/stub output for the agent. Pass
`format="json"` when the agent needs to navigate fields programmatically.

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
- `infra-mcp-manifest-generator-python`: Automated distribution scaffolding.
- `universal-agent-response-python`: Standardized JSON schema.
- `universal-list-paginator-python`: Result set pagination.

---

## License

Licensed under the Apache License, Version 2.0. See the [LICENSE](LICENSE) file for details.
