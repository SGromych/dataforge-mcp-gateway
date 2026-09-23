# Transport design decisions

A record of the choices behind the Streamable HTTP transport (v0.3.0), the options weighed
against each, and what would make us revisit them. Nothing here is settled forever — the
point of writing it down is that any single decision can be reversed without re-deriving
the analysis.

Each entry: **Context** → **Options** → **Decision** → **Revisit when**.

| # | Decision | Status |
|---|---|---|
| [1](#1-build-on-the-sdks-streamablehttpsessionmanager) | Build on the SDK's `StreamableHTTPSessionManager` | Settled |
| [2](#2-optional-bearer-token-on-the-endpoint) | Optional bearer token on the endpoint | Settled with the owner |
| [3](#3-one-dataforge-key-from-env-no-per-request-pass-through) | One DataForge key from env | Settled with the owner |
| [4](#4-keep-the-sse-transport-mark-it-deprecated) | Keep SSE, mark it deprecated | Settled with the owner |
| [5](#5-docker-defaults-to-streamable-http-the-process-default-stays-stdio) | Docker defaults to streamable-http | Settled with the owner |
| [6](#6-stateful-sessions-by-default) | Stateful sessions by default | Settled |
| [7](#7-three-way-derivation-of-origin-validation) | Three-way derivation of Origin validation | Settled |
| [8](#8-authentication-as-raw-asgi-middleware) | Authentication as raw ASGI middleware | Settled |
| [9](#9-mount-the-endpoint-as-an-asgi-class-instance) | Mount the endpoint as an ASGI class instance | Settled |
| [10](#10-split-the-module-so-tests-need-no-socket) | Split the module so tests need no socket | Settled |
| [11](#11-comma-separated-strings-for-list-valued-settings) | Comma-separated strings for list settings | Settled |
| [12](#12-validate-mcp_transport-and-fail-loudly) | Validate `MCP_TRANSPORT` and fail loudly | Settled |
| [13](#13-no-eventstore-streams-are-not-resumable) | No `EventStore`, streams not resumable | **Deferred** |
| [14](#14-target-the-session-based-revisions-not-the-2026-07-28-draft) | Target session-based revisions, not the draft | **Deferred** |
| [15](#15-raise-the-mcp-floor-to-126) | Raise the `mcp` floor to 1.26 | Superseded by [18](#18-move-to-the-mcp-sdk-2x) |
| [16](#16-register-both-mcp-and-mcp) | Register both `/mcp` and `/mcp/` | Settled |
| [17](#17-collapse-transport-dispatch-into-one-function) | Collapse transport dispatch into one function | Settled |
| [18](#18-move-to-the-mcp-sdk-2x) | Move to the MCP SDK 2.x | Settled with the owner |

---

## 1. Build on the SDK's `StreamableHTTPSessionManager`

**Context.** Open WebUI speaks Streamable HTTP only; the server had stdio and the
deprecated HTTP+SSE. Something had to implement the newer transport.

**Options.**

*Use the `mcp` SDK's `StreamableHTTPSessionManager`.*
Pros: already installed (mcp 1.26.0) with no new dependency; implements session handling,
SSE framing, content negotiation and protocol-version negotiation; tracks the spec as the
SDK is upgraded; the project keeps its existing low-level `Server` and all 65 tools
untouched.
Cons: we inherit the SDK's choices, including which protocol revisions are supported.

*Hand-roll the transport.*
Pros: total control; could implement the 2026-07-28 draft ahead of the SDK.
Cons: re-implements session management, SSE framing, negotiation and cancellation — a lot
of protocol surface to get wrong, with no upstream fixes. Nothing about this gateway is
unusual enough to justify it.

*Rewrite the server on `FastMCP`.*
Pros: `streamable_http_app()` gives the app in one call.
Cons: a rewrite of `mcp/tools*.py`, the handler registry and the `ToolAnnotations` wiring
for a transport change. FastMCP's decorator model does not fit a 65-tool flat registry
built from schema fragments. Large blast radius, no gain.

*Ship nothing; tell users to run the `mcpo` proxy.*
Pros: zero code.
Cons: an extra process to deploy and secure for every user; the gateway still cannot be
reached by a conforming HTTP client on its own. Pushes our problem onto users.

**Decision.** The SDK's session manager, wrapped in our own Starlette app so auth,
health, CORS and logging stay ours.

**Revisit when.** The SDK stops tracking the spec, or we need transport behaviour it
refuses to expose.

---

## 2. Optional bearer token on the endpoint

**Context.** 38 of 65 tools write to DataForge, including permanent deletion of projects
and versions. stdio implies process ownership; an HTTP port does not. The existing SSE
transport shipped with no authentication at all.

**Options.**

*Optional `MCP_AUTH_TOKEN`; unset means open, with a loud startup warning.*
Pros: secure deployments are one variable away; `curl` and Inspector against localhost
stay frictionless; Open WebUI supports Bearer natively.
Cons: the insecure configuration is still reachable — a warning in a log is easy to miss.

*Mandatory for the HTTP transports: refuse to start without a token.*
Pros: the unsafe state is unreachable.
Cons: breaks a one-line local run and every existing SSE deployment; pushes people toward
a dummy token, which is worse than an informed choice.

*No authentication; rely on the network perimeter and the key's role.*
Pros: least code.
Cons: any reachable port becomes delete rights. The gateway's own `.env.example` already
warns that the key's role is the only limit — adding a network-reachable surface with no
second limit is not a trade we should make for the user.

*Full OAuth 2.1 provider.*
Pros: per-user identity; Open WebUI supports it including Dynamic Client Registration.
Cons: a large subsystem — registration, metadata discovery, token lifecycle — for an
internal gateway whose authorization decisions are made by DataForge anyway. A proxy can
terminate OAuth in front if it is ever needed.

**Decision.** Optional token. Unset is permitted; a non-loopback bind without one logs a
warning naming the consequence, and the docs treat the token as required for anything but
localhost.

**Revisit when.** The gateway is exposed outside a trusted network, or several teams share
one deployment and need per-user identity — then option 4, most likely via a proxy.

---

## 3. One DataForge key from env, no per-request pass-through

**Context.** Open WebUI can inject `{{USER_ID}}` / `{{USER_EMAIL}}` into custom headers,
so each of its users could in principle present their own DataForge key.

**Options.**

*One `DATAFORGE_API_KEY` for the process.*
Pros: no change to `SemanticService`, the client or the cache; one predictable permission
level that an operator can reason about; the cache stays shared and effective.
Cons: every caller acts with the same DataForge rights and appears as the same principal
in the audit log.

*Per-request key via an `X-DataForge-Api-Key` header.*
Pros: each user gets their own DataForge permissions, and the audit log attributes writes
to a real person — genuinely valuable given what the write tools can delete.
Cons: the key must thread through the MCP handler, `SemanticService` and the client, which
are all built around one long-lived `DataForgeClient`; the cache must be partitioned per
key or it leaks data between users; a client that forgets the header silently falls back
to the env key, which is a quiet privilege escalation. A substantially larger change than
the transport itself.

**Decision.** One key from env. The bearer token controls who reaches the endpoint; the
DataForge key controls what they can do.

**Revisit when.** Multiple teams share a deployment, or an audit requires writes
attributed to individuals. The cache partitioning is the real work, not the header.

---

## 4. Keep the SSE transport, mark it deprecated

**Context.** `MCP_TRANSPORT=sse` exists and may be in use. The spec deprecated HTTP+SSE in
revision 2025-03-26.

**Options.**

*Keep it, warn at startup and in the docs.*
Pros: nothing breaks; the migration path is documented; the code is 48 lines and stable.
Cons: a deprecated, unauthenticated transport stays shipped.

*Remove it.*
Pros: one HTTP transport to document, test and secure.
Cons: breaks any existing deployment for no functional gain.

*Keep it as a peer with no warning.*
Pros: none beyond brevity.
Cons: leaves people adopting a transport the spec has retired.

**Decision.** Keep it; `run_transport` logs `transport_deprecated` on startup, the module
docstring and every doc page say so, and [transports.md](transports.md#migrating-off-sse)
carries a three-step migration.

**Revisit when.** No known deployment still uses it — then delete `transport/sse.py` and
drop `sse` from `TRANSPORTS`.

---

## 5. Docker defaults to streamable-http; the process default stays stdio

**Context.** `docker-compose.yml` set `MCP_TRANSPORT=sse`. The container scenario is
exactly the Open WebUI one.

**Options.**

*Compose switches to `streamable-http`; `Settings.mcp_transport` stays `stdio`.*
Pros: `docker compose up` produces the endpoint people actually want; local stdio use is
untouched, so Claude Desktop needs no configuration change.
Cons: a container rebuild changes the wire protocol for anyone who relied on the compose
file's SSE default.

*Leave compose on `sse`.*
Pros: no change for existing compose users.
Cons: the documented Docker path keeps producing a deprecated endpoint.

*Make `streamable-http` the global default.*
Pros: one default everywhere.
Cons: every stdio client breaks — the server would bind a port instead of talking over
stdout. Clearly wrong.

**Decision.** Compose uses `streamable-http`; the process default remains `stdio`.

**Revisit when.** stdio stops being the majority local case.

---

## 6. Stateful sessions by default

**Context.** The session manager supports `stateless` and `json_response`.

**Options.**

*Stateful and SSE by default, both alternatives opt-in.*
Pros: matches the spec's primary shape and what clients expect; keeps server-initiated
notifications and progress available; `MCP_STATELESS` / `MCP_JSON_RESPONSE` cover the
other cases.
Cons: sessions live in process memory, so a horizontally scaled deployment needs session
affinity.

*Stateless by default.*
Pros: trivially scalable; no session expiry to explain.
Cons: gives up server-initiated notifications for every user to benefit the few running
more than one replica.

*JSON-only by default.*
Pros: easier to debug with `curl`.
Cons: no streaming progress on long calls, and long-running writes are exactly where
progress helps.

**Decision.** Stateful and SSE by default; both alternatives are one variable away and
both are covered by tests.

**Revisit when.** A multi-replica deployment without session affinity becomes the norm.

---

## 7. Three-way derivation of Origin validation

**Context.** The spec says servers **MUST** validate `Origin`. The SDK's
`TransportSecuritySettings` enables protection with empty allow-lists — which rejects
every request. `TransportSecurityMiddleware` defaults to protection *off* when passed
`None`.

**Options.**

*Derive: explicit allow-list → loopback defaults → off with a warning.*
Pros: localhost is protected with no configuration; Docker works out of the box; a
deliberate allow-list is always honoured; the unprotected case announces itself.
Cons: the public-bind default is technically a spec deviation, and it is the default in
the shipped compose file.

*Always on.*
Pros: spec-conforming everywhere.
Cons: with no allow-list it rejects everything, so the shipped Docker setup would be
broken on arrival. A container's authority — `host.docker.internal`, a service name, a
proxy's `Host` — cannot be guessed.

*Always off.*
Pros: never surprises anyone.
Cons: abandons a requirement that exists for a real attack, including on the localhost
deployments where it costs nothing.

**Decision.** Derive, and warn in case 3. `MCP_ALLOWED_HOSTS` moves a deployment to case 1
in one line, which the Docker docs and compose comments both point at.

**Revisit when.** We can detect the container's external authority reliably, or the SDK
grows a sane default for reverse-proxied deployments.

---

## 8. Authentication as raw ASGI middleware

**Context.** The token check has to run in front of an endpoint whose responses are
long-lived SSE streams.

**Options.**

*Raw ASGI callable.*
Pros: `send` passes through untouched, so streaming is unaffected; no task-group overhead
per request; trivially testable.
Cons: works with raw byte headers rather than Starlette's `Request`.

*`BaseHTTPMiddleware`.*
Pros: ergonomic `Request`/`Response` API.
Cons: wraps every response in an anyio task pair and buffers it — the documented cause of
broken SSE streaming under Starlette. Disqualifying here.

*Check inside the endpoint.*
Pros: no middleware.
Cons: mixes transport auth into request handling and would have to be repeated for the
health route and any future route.

**Decision.** Raw ASGI, in `transport/auth.py`, with `hmac.compare_digest` and `/health`
exempt.

**Revisit when.** Auth grows beyond a shared secret — then it likely belongs in a proxy
anyway (see decision 2).

---

## 9. Mount the endpoint as an ASGI class instance

**Context.** Starlette's `Route.__init__` inspects its endpoint: `inspect.isfunction` or
`inspect.ismethod` means "HTTP handler", and it is wrapped with `methods=["GET"]`.

**Options.**

*Wrap the manager in a small class with `__call__`.*
Pros: neither a function nor a method, so Starlette treats it as a raw ASGI app and lets
POST, GET and DELETE through; this is exactly what the SDK's own `FastMCP` does.
Cons: a few lines of boilerplate that look redundant until you know why.

*Pass `manager.handle_request` directly.*
Pros: looks cleaner.
Cons: **silently breaks every POST with a 405.** The obvious spelling is the broken one.

*Use `Mount` instead of `Route`.*
Pros: also routes all verbs.
Cons: `Mount` rewrites `root_path`/`path` and matches by prefix, so `/mcp/anything` would
resolve; exact-path routing is what the spec describes.

**Decision.** `StreamableHTTPASGIApp`, with the reason in its docstring and a test
(`test_endpoint_accepts_post`) that fails if someone "simplifies" it.

**Revisit when.** Never, unless Starlette changes its endpoint inspection.

---

## 10. Split the module so tests need no socket

**Context.** The session manager must be inside `async with manager.run()` before it can
serve, and `httpx.ASGITransport` does not run a Starlette lifespan.

**Options.**

*Expose `create_session_manager`, `build_app` and `run_streamable_http` separately.*
Pros: a test enters `manager.run()` itself and drives `build_app(...)` through
`httpx.ASGITransport` — real ASGI, real routing, real middleware, no socket, no new
dependency; the full suite still runs in under a minute.
Cons: three functions where one would do, and the lifespan path is only exercised in the
live smoke check.

*Add the `asgi-lifespan` dev dependency.*
Pros: exercises the real lifespan.
Cons: a new dependency to test code we control, for one context manager.

*Bind a real socket in tests.*
Pros: closest to production.
Cons: port conflicts, startup races and flakiness in CI, for no coverage the ASGI route
misses.

**Decision.** Split the module. The live path was verified by hand against a real uvicorn
process — full handshake, 65 tools listed, session DELETE, 404 afterwards.

**Revisit when.** Lifespan behaviour itself becomes complex enough to need its own test.

---

## 11. Comma-separated strings for list-valued settings

**Context.** `MCP_ALLOWED_HOSTS`, `MCP_ALLOWED_ORIGINS` and `MCP_CORS_ORIGINS` are lists.

**Options.**

*Store as `str`, expose `*_list` properties that split and strip.*
Pros: `.env` stays readable — `MCP_ALLOWED_HOSTS=a:8080,b:8080`; matches how every other
tool spells such a variable; empty entries and stray spaces are tolerated.
Cons: the typed value is not the list; two names exist for one concept.

*Declare them `list[str]`.*
Pros: correct type on the model.
Cons: pydantic-settings parses complex types as **JSON**, so the variable would have to be
`["a:8080","b:8080"]` — quoting that in a compose file or a shell is a trap.

**Decision.** Strings plus properties, with the reason recorded at `_split_csv`.

**Revisit when.** pydantic-settings offers a first-class delimited-list source.

---

## 12. Validate `MCP_TRANSPORT` and fail loudly

**Context.** Dispatch was `if sse: ... else: stdio`, so any unrecognised value started
stdio in silence.

**Options.**

*Validate in `Settings`, reject unknown values, normalise obvious aliases.*
Pros: `MCP_TRANSPORT=streamable_http` works instead of silently starting stdio — a very
likely typo given the hyphen; a wrong value fails at startup with a message naming the
valid ones; `TRANSPORTS` feeds the argparse `choices`, so CLI and config cannot drift.
Cons: a value that used to "work" (start stdio) now raises.

*Keep the fallback.*
Pros: never fails to start.
Cons: the failure surfaces much later as "why is nothing listening on 8080", with no clue
in the logs.

**Decision.** Validate. `validate_assignment=True` extends the same checks to the CLI's
writes onto `Settings`.

**Revisit when.** Never.

---

## 13. No `EventStore`: streams are not resumable

**Status: deferred, not rejected.**

**Context.** Revisions through 2025-11-25 allow a client to resume a dropped SSE stream
with `Last-Event-ID`, if the server keeps an `EventStore`. The SDK ships the interface but
no implementation.

**Options.**

*Pass `event_store=None`.*
Pros: no code, no memory growth, no expiry policy to design. A dropped stream costs one
re-sent request, and this gateway's calls are short — a tool call is one DataForge round
trip, not a long generation.
Cons: a flaky network re-runs the request. For a *write* tool that re-run is a genuine
concern, though `Idempotency-Key` already makes a retried POST safe at the DataForge end.

*Implement an in-memory `EventStore`.*
Pros: resumable streams; fewer repeated calls on bad links.
Cons: unbounded memory without an eviction policy; state that must be reasoned about on
restart and across replicas; and the 2026-07-28 draft removes resumability entirely, so
this could be built and then deleted.

**Decision.** No `EventStore` for now. Recorded here so the absence is a choice, not an
oversight.

**Revisit when.** Users report dropped streams on long-running tools — most plausibly
`df_generate_sql` or a version export — and decision 14 has settled.

---

## 14. Target the session-based revisions, not the 2026-07-28 draft

**Status: deferred, not rejected.**

**Context.** The draft spec (`2026-07-28`) changes Streamable HTTP substantially: no
protocol-level sessions, no GET stream, no resumability, and new mandatory request
metadata headers (`Mcp-Method`, `Mcp-Name`, `MCP-Protocol-Version` matched against the
body). The installed SDK supports `2024-11-05` through `2025-11-25`.

**Options.**

*Ship what the SDK supports.*
Pros: interoperates with every client that exists today, Open WebUI included; sessions
and the GET stream are what those clients expect; upgrading the SDK later brings the new
revision with it.
Cons: a future client speaking only the draft will not connect until the SDK catches up.

*Pre-implement the draft.*
Pros: ready early.
Cons: would mean bypassing the session manager and hand-rolling the transport — undoing
decision 1 — to support a revision no client speaks yet, against a spec still labelled
draft and still changing.

**Decision.** Ship the SDK's revisions. The docs state which ones are supported, so the
gap is visible.

**Revisit when.** The SDK adds draft support — likely just a version bump plus tests — or
a client we need speaks only the new revision.

---

## 15. Raise the `mcp` floor to 1.26

**Context.** `pyproject.toml` declared `mcp>=1.0`. `StreamableHTTPSessionManager` does not
exist in early 1.x, and `streamable_http_client` (used by the tests) is newer still.

**Options.**

*Pin `>=1.26`, the version developed and tested against.*
Pros: the declared floor is a version we have actually run; an older resolve fails at
install time with a clear message instead of at import time with `ImportError`.
Cons: stricter than strictly necessary — some earlier 1.x would probably work.

*Keep `>=1.0`.*
Pros: permissive.
Cons: advertises support for versions where the transport cannot even be imported.

*Find the exact minimum by bisecting SDK versions.*
Pros: the truest floor.
Cons: real work to pin a number that matters only to someone deliberately holding back the
SDK, and it would still need re-verifying on every SDK change.

**Decision.** `mcp>=1.26`.

**Revisit when.** Someone needs an older SDK — then bisect and lower it deliberately.

**Superseded** by decision 18: the floor is now `2.2` and the range is bounded above.

---

## 16. Register both `/mcp` and `/mcp/`

**Context.** Starlette answers the non-matching slash variant with a 307 redirect.

**Options.**

*Register both paths against the same endpoint instance.*
Pros: both spellings work identically; no redirect for a client to mishandle. One line.
Cons: two routes for one endpoint.

*Rely on `redirect_slashes`.*
Pros: nothing to write.
Cons: HTTP clients vary in whether they preserve the method and body across a 307, and a
redirect on POST is a classic source of "it works in curl but not in my client".

**Decision.** Register both.

**Revisit when.** Never.

---

## 17. Collapse transport dispatch into one function

**Context.** The same `if/else` lived in `main.py` and `cli.py`, and argparse `choices`
was a third place to edit per transport.

**Options.**

*One `run_transport(server, settings)` in `transport/__init__.py`, with `choices` fed
from `TRANSPORTS`.*
Pros: a new transport touches one function and one tuple; both entry points provably agree
because they call the same code; the deprecation warning lives in one place.
Cons: a small refactor riding along with a feature change.

*Add a third copy.*
Pros: smaller diff.
Cons: three places to keep in sync, which is how `cli.py` already lagged behind.

**Decision.** One dispatcher, covered by `tests/test_transport_dispatch.py`.

**Revisit when.** Never.

---

## 18. Move to the MCP SDK 2.x

**Context.** The dependency was `mcp>=1.26` with no upper bound, so a fresh install
resolved to 2.2.0, where the low-level `Server` no longer has the `list_tools()` /
`call_tool()` decorators. The process died at startup with `AttributeError` — found by
running the gateway against a live DataForge instance, not by any test, because the test
environment already had 1.x installed.

**Options.**

*Bound the range at `<2` and stay on 1.x.*
Pros: one line; nothing else moves.
Cons: freezes the server on a line that will stop receiving fixes, and every new install
of the SDK diverges further from what we run.

*Support both 1.x and 2.x behind a compatibility shim.*
Pros: nobody has to upgrade.
Cons: the handler signatures differ (`(name, arguments) -> list[TextContent]` against
`(context, params) -> CallToolResult`), so the shim spreads into the one place that must
stay obvious, and the tests would have to run twice to mean anything.

*Move to 2.x.*
Pros: current SDK; its lowlevel server no longer validates tool arguments, which is
exactly where the bare `Input validation error: …` came from; the transports, security
settings and session manager kept their names and signatures, so the move touched three
files.
Cons: 1.x installs stop working — a breaking change for anyone pinning the old SDK.

**Decision.** Move to 2.x: `mcp>=2.2,<3`. The upper bound stays this time, because the
2.x break is exactly the lesson: `Server` is a low-level API and a major release may
rearrange it. Argument validation moved into `mcp/arguments.py`, which also made the
error envelope consistent — see [schemas.md](schemas.md#tool-arguments).

**Measured after the move:** the full suite (502 tests) passes on 2.2.0 with starlette
1.7; `tools/list` returns all 65 tools over the wire; a mismatched `MCP-Protocol-Version`
now answers 400 *with* a JSON-RPC error message, which 1.x left blank.

**Revisit when.** 3.x appears — the same way: try it, run the suite, decide.

---

## See also

- [transports.md](transports.md) — how to use the transports
- [open-webui.md](open-webui.md) — the use case that prompted this work
