# Connecting to Open WebUI

Open WebUI talks to external MCP servers over **Streamable HTTP only** — stdio and the
deprecated HTTP+SSE transport need the separate `mcpo` proxy. This server speaks
Streamable HTTP natively, so no proxy is required.

> ## ⚠️ Read this before connecting a production key
>
> Once connected, every Open WebUI user who can use the tools can invoke all 65 of them —
> including the 38 that **create, overwrite and permanently delete** DataForge data, up to
> whole projects and versions. There is no read-only switch in this server, and **all Open
> WebUI users share one DataForge key**, so they all act with that key's rights and appear
> as that key in the audit log.
>
> - Start with a `viewer` or `analyst` key: writes then fail with
>   `403 DF_API.WRITE_ACCESS_DENIED` and the server is effectively read-only.
> - Point it at a non-production project version first.
> - Set `MCP_AUTH_TOKEN`. Open WebUI reaches the server over the network, and without a
>   token so can anything else on that network.
>
> See [configuration.md](configuration.md#-dataforge_api_key-decides-what-an-agent-can-destroy)
> for what each role can destroy.

---

## 1. Start the server

Generate a token first:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### With Docker (recommended)

```bash
cp .env.example .env
```

In `.env` set at least:

```bash
DATAFORGE_API_KEY=your_dataforge_key
MCP_AUTH_TOKEN=the_token_you_just_generated

# The authority Open WebUI will use, so Origin validation can be switched on.
MCP_ALLOWED_HOSTS=host.docker.internal:8080,localhost:8080
```

Then:

```bash
docker compose up -d
docker compose ps        # STATUS should become "healthy"
curl -s http://localhost:8080/health
# {"status":"ok"}
```

`docker-compose.yml` already sets `MCP_TRANSPORT=streamable-http`, `HOST=0.0.0.0`,
`PORT=8080` and `MCP_HTTP_PATH=/mcp`.

### Without Docker

```bash
MCP_TRANSPORT=streamable-http \
MCP_AUTH_TOKEN=the_token_you_just_generated \
HOST=0.0.0.0 PORT=8080 \
python -m dataforge_mcp
```

---

## 2. Work out the URL

This is where most connection failures come from. `localhost` inside the Open WebUI
container means *that container*, not your machine.

| Where Open WebUI runs | Where this server runs | URL to enter |
|---|---|---|
| Docker | on the host | `http://host.docker.internal:8080/mcp` |
| Docker | another container, same compose network | `http://dataforge-mcp:8080/mcp` |
| Docker | another host | `http://<host-or-ip>:8080/mcp` |
| Natively on the host | on the same host | `http://localhost:8080/mcp` |
| Anywhere | behind a TLS proxy | `https://mcp.example.com/mcp` |

On Linux, `host.docker.internal` needs an explicit mapping — add to the Open WebUI
service:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

Whatever authority you land on must appear in `MCP_ALLOWED_HOSTS` if Origin validation is
on. It is on automatically for a loopback bind, and off with a warning for a public bind
until you set the variable — see
[transports.md](transports.md#origin-validation-and-dns-rebinding-protection).

---

## 3. Add the connection in Open WebUI

MCP servers can only be registered by an **administrator**.

1. **Settings → Admin → Integrations**.
2. Under *External Tool Servers*, click **+ Add Connection**.
3. **Type**: `MCP (Streamable HTTP)`.
4. **URL**: the one from step 2, path included (`…/mcp`).
5. **Auth**: `Bearer`, and paste the `MCP_AUTH_TOKEN` value.
   Leaving the key empty with Bearer selected is rejected.
6. **Save**, and restart if prompted.

Open WebUI also supports OAuth 2.1 for MCP connections. This server does not implement it
— use `Bearer`, or terminate OAuth at a proxy in front.

---

## 4. Verify

In Open WebUI the connection should list **65 tools**. A quick functional check from a
chat, in order of increasing risk:

- `df_health` — no DataForge call, proves the transport works.
- `df_list_projects` — proves the API key and network path work.
- `df_get_measures` for a project/version — proves normalization works.

From the shell, the same handshake is in
[transports.md](transports.md#worked-example).

Server-side, a successful startup logs:

```json
{"transport":"streamable-http","host":"0.0.0.0","port":8080,"path":"/mcp",
 "auth":"bearer","dns_rebinding_protection":true,"json_response":false,
 "stateless":false,"cors":false,"event":"mcp_transport_starting","level":"info"}
```

If `auth` reads `"none"` or `dns_rebinding_protection` is `false`, the server also emits a
warning saying what to set.

---

## Custom headers and per-user identity

Open WebUI can expand `{{USER_ID}}`, `{{USER_EMAIL}}`, `{{USER_ROLE}}` and `{{CHAT_ID}}`
into custom headers on an MCP connection.

**This server ignores them.** It deliberately does not map a header to a per-user
DataForge key: one `DATAFORGE_API_KEY` governs every caller, so that key's project role is
the only permission boundary, and the DataForge audit log attributes every write to it
rather than to the individual who asked.

That is a recorded decision, not an oversight — the reasoning, and what per-user keys
would cost, are in
[transport-decisions.md](transport-decisions.md#3-one-dataforge-key-from-env-no-per-request-pass-through).
Until it changes, scope access with the API key's role and with who can use the tools in
Open WebUI.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Connection test fails, no server log line | Open WebUI never reached the server | Wrong host — see the URL table; on Linux add the `host.docker.internal` mapping |
| `401` in the server log | Token missing or wrong | Auth = `Bearer`, key = `MCP_AUTH_TOKEN` exactly; no `Bearer ` prefix in the field |
| `421 Misdirected Request` | `Host` not allow-listed | Add the authority, port included, to `MCP_ALLOWED_HOSTS` |
| `404` on the endpoint | Path missing from the URL | It must end in `/mcp`, not the bare host |
| Connects, but zero tools listed | Pointed at `/sse` | Streamable HTTP uses `/mcp` |
| Tools listed, every call errors | DataForge key wrong or unreachable | Check `DATAFORGE_API_KEY` and `DATAFORGE_BASE_URL`; call `df_health` |
| Writes fail with `403 WRITE_ACCESS_DENIED` | Key is `viewer`/`analyst` | Expected for a read-only key — raise the role only if you mean to |
| Tool calls hang | A proxy is buffering the SSE stream | `proxy_buffering off` — see [transports.md](transports.md#behind-a-reverse-proxy) |
| Container never becomes `healthy` | Server not listening | `docker compose logs dataforge-mcp`; a bad `MCP_TRANSPORT` fails at startup |

---

## See also

- [transports.md](transports.md) — the transport reference
- [transport-decisions.md](transport-decisions.md) — why it works this way
- [Open WebUI MCP documentation](https://docs.openwebui.com/features/extensibility/mcp/)
