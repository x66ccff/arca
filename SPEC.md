# Arca Folder Protocol v1

This document defines the portable data contract. Implementations may be
written in any language and do not need to invoke the bundled CLI.

## 1. Canonical state

For each paper, canonical state is the directory:

```text
papers/<paper-key>/metadata.json
papers/<paper-key>/notes/summary.md
papers/<paper-key>/notes/annotations.jsonl
papers/<paper-key>/paper.pdf
graph/edges.jsonl
```

`metadata.json` MUST be UTF-8 RFC 8259 JSON and SHOULD end with a newline.
`notes/summary.md` MUST be UTF-8 Markdown. Each non-empty line in
`notes/annotations.jsonl` MUST be one annotation object following
`schema/annotation.schema.json`. `paper.pdf` MUST contain the original PDF
bytes. Extra files are allowed and SHOULD be declared under `files`.

`graph/edges.jsonl` is canonical. Each non-empty line MUST be one relation
object following `schema/edge.schema.json`. Edge endpoints use stable paper
IDs, not directory paths, so links survive folder moves.

The generated `_index/` directory MUST NOT be treated as canonical state.

## 2. Paper key

For modern arXiv IDs the key is the versionless ID, for example
`2203.11171`. A legacy ID replaces `/` with `__`, for example
`cs__0601001`. Other providers SHOULD use `<provider>__<provider-id>`.

Keys MUST match `^[A-Za-z0-9._-]+$` and MUST NOT contain path separators.

## 3. Mutation rules

1. Write to a temporary file in the same filesystem.
2. Flush and atomically replace the destination.
3. Rebuild `_index/catalog.jsonl` after canonical changes.
4. Preserve unknown metadata fields during updates.
5. Never infer successful PDF storage from a URL alone; verify bytes and hash.
6. A delete SHOULD be recoverable by moving the whole paper directory to
   `.trash/`.

## 4. Concurrency

Writers SHOULD acquire the `.arca.lock/` directory with atomic `mkdir` before
mutating canonical state. Readers MAY proceed without the lock because file
replacement is atomic. A writer MUST release the lock on normal or exceptional
exit.

## 5. Index contract

`_index/catalog.jsonl` contains one JSON object per line, sorted by paper ID.
It is optimized for streaming tools such as `rg`, `jq`, Python, Go, Rust, or
JavaScript. `_index/paper-graph.html` MAY contain a generated standalone
visualization. Consumers MUST tolerate every `_index/` artifact being absent
and MAY rebuild them from canonical metadata and `graph/edges.jsonl`.

## 6. Notes and annotations

`summary.md` is intentionally unstructured and may link to another record with
the stable `arca:<paper-id>` form. Structured PDF annotations contain a UUID,
optional 1-based page number, optional quote, comment, tags, and timestamps.
Implementations MUST preserve unknown annotation fields.

## 7. Paper graph

Each edge has a UUID, `from`, `to`, `type`, `directed`, an optional note, and a
creation timestamp. Recommended types are `cites`, `extends`, `contrasts`,
`supports`, `challenges`, `uses`, `reproduces`, `similar`, and
`discussed-with`. Custom types are allowed. Readers SHOULD tolerate a missing
endpoint when a paper is temporarily in `.trash/`.

## 8. Forward compatibility

Readers MUST reject an unsupported `schema_version` only when required fields
cannot be interpreted. They SHOULD preserve unknown keys. New optional fields
may be added without changing the folder layout.
