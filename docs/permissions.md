# Permissions and Safety Boundary

Plain-language statement of what this project is allowed to do to a scan
target (brief Section 2, item 3 — this boundary is permanent).

## What the scanner does

- Connects to a target MCP server as a client (stdio command or HTTP URL).
- Reads metadata only: `list_tools`, `list_resources`, `list_prompts`, and
  the schemas/descriptions/annotations they return.

## What the scanner never does

- It **never invokes a target server's tools** (`call_tool`).
- It **never reads a target's resources** (`read_resource`) or executes its
  prompts — it only reads their listed metadata.
- It **never feeds target metadata to an LLM.** The rule engine is
  deterministic (pattern/heuristic/schema-shape based). Feeding untrusted
  tool descriptions to an LLM would reintroduce the exact prompt-injection
  risk this tool exists to detect.

## Decision model (Phase 5)

- The hosted decision model receives only data the scanner produced:
  finding counts per severity, triggered rule IDs, transport type, and the
  `allow_external` flag.
- It **never receives target-server text**: no names, descriptions, schemas,
  finding text, URLs, commands, or args.
- It can make a verdict stricter, never less strict. Any Critical finding is
  always `block`.

## Target restrictions

- Default targets are localhost or self-hosted fixture servers only.
- Any non-localhost target requires an explicit `allow_external` consent
  flag in both API and UI; granting it is logged. Scan only servers you own
  or are authorized to assess.

## Agent extension pack (Phase 2, if in scope)

The same boundary applies to the `mcp-server/` component that exposes this
scanner's own functions as MCP tools: those tools trigger enumeration-only
scans and read stored reports — nothing else.
