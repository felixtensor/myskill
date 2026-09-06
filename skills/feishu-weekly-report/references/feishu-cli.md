# Optional Feishu CLI Reads and Capability Boundaries

Official documentation and live CLI approval metadata were checked on 2026-09-06. This was public-document research, not a tenant integration test. Recheck installed help and current official documentation when capabilities change.

## Role in this skill

Use an available authenticated Feishu connector, official CLI, or page reader for source retrieval and form discovery. No transport is a universal prerequisite. A working source reader does not establish the ability to fill the destination page.

The official [CLI capability explanation](https://www.feishu.cn/content/article/7641519075810069471) states that CLI wraps OpenAPI and does not perform UI automation. The [approval initiation reference](https://github.com/larksuite/cli/blob/main/skills/lark-approval/references/lark-approval-initiate.md) documents instance creation as starting approval; dry-run only previews the request.

The CLI [registry implementation](https://github.com/larksuite/cli/blob/7fd6ef3c07182257ce776cdc5a614e122d5bd4b3/internal/registry/remote.go) loads remote API definitions. The checked [public metadata](https://open.feishu.cn/api/tools/open/api_definition?protocol=meta&client_version=v1.0.42) exposed approval definition search/get, instance get/create/cancel/cc/initiated, and task actions. Its approval service contained no draft operation; creation used `POST instances/initiate` without a save-draft flag. The native [v4 instance creation API](https://open.feishu.cn/document/server-docs/approval-v4/instance/create) also provides no documented unsubmitted-draft mode. Its resubmission flags are not draft controls.

These findings bound the supported route checked here; they are not a claim about every future API. Do not invent draft endpoints or replay private client requests. A tool called “create” or “draft” needs documented semantics for native approval form drafts, not mail, dictionary, or approval-definition drafts. This skill uses the live page route for filling and persistence, and does not execute approval creation or submission commands.

The official [personal MCP service notice](https://open.feishu.cn/document/mcp_open_tools/end-user-call-remote-mcp-server) concerns the phased retirement of the personal managed MCP Token route and recommends CLI. It does not announce retirement of every MCP implementation. Evaluate an existing connector's actual read capabilities rather than requiring its replacement by name.

## Local CLI discovery

When Feishu reads are relevant, check for the official executable without installing anything:

```bash
command -v lark-cli
```

On PowerShell:

```powershell
Get-Command lark-cli -CommandType Application -ErrorAction SilentlyContinue
```

If found, run the resolved executable with `--version`, then inspect relevant help and `lark-cli auth status`. A PATH miss does not prove system-wide absence: check a user-provided or known installer-reported location if available. Do not scan the whole disk or use `npx` as an installation check.

Installed, executable, command-capable, authenticated, and authorized are separate states. Reuse the correct tenant and identity; do not switch accounts or bot/user identity silently. Do not dump credential configuration.

## Setup only when needed for a selected read route

If existing readers suffice, proceed without installing CLI. If CLI is the needed route for Feishu evidence or definition reads, follow the current [official quick start](https://github.com/larksuite/cli#quick-start-ai-agent) under host permissions. The documented installer is `npx @larksuite/cli@latest install`; it requires network and installation-directory access. Verify Node/npm availability and the official package before execution.

Reuse existing configuration. When needed, inspect `config init --help` and `auth login --help`, use the official guided setup, and let the user complete account-bound authentication and choices through the returned official URL or QR code. Request only necessary read permissions. New-app configuration is a setup action, not a connectivity check.

Document access and approval-definition access have separate scopes. Identify missing login, source access, or administrator permission specifically; reinstalling does not fix an access denial. Resume from the prepared work once resolved. Setting up CLI cannot resolve missing destination UI access.

## Read-only approval discovery

Verify installed help before using these documented commands. `周报` is a literal form search term. Construct dynamic JSON with a serializer and safe argument passing.

```bash
lark-cli approval approvals search --data '{"keyword":"周报"}' --as user
lark-cli approval approvals get --params '{"approval_code":"APPROVAL_CODE"}' --as user
```

Replace the placeholder with an actual supplied or returned definition code. Search only if needed, follow pagination, and distinguish multiple matches by group and structure. Ask only if the target remains ambiguous. Use actual returned links; do not derive a URL from a code by guesswork.

The definition's `form` helps interpret IDs, types, options, and nested controls. It is not the current form's edited values. Read current content through the page. External definitions require inspecting the actual linked application rather than treating it as native approval.

If already-submitted status needs clarification and the read capability is available, inspect candidates using `approval instances initiated` and `approval instances get` with current help. Creation time is not the reporting period; verify contents before declaring a match. Submitted-instance searches do not discover unsubmitted client drafts.

For document commands, read [work-source guidance](work-sources.md#feishu-documents). Open Platform pages with unreadable HTML may have a readable `.md` version. Keep public references here, never tenant snapshots or private links.
