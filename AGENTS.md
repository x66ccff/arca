# Agent operating contract

Arca is a file protocol first and a CLI second.

## Preferred path

1. Read `manifest.json` and verify `format == "arca-library"`.
2. Query with `./arca --library <path> search <query> --jsonl`.
3. Retrieve one record with `get <id> --json` and its local directory with
   `path <id>`.
4. Mutate through the CLI when possible.
5. After any direct filesystem mutation, run `reindex` then `doctor`.
6. Generate the standard interactive graph with
   `./arca --library <path> visualize`; do not hand-write a replacement unless
   the user asks for a different visual encoding.

## Rules

- Treat `papers/*/metadata.json`, `notes.md`, and declared files as canonical.
- Never edit `_index/catalog.jsonl` as a source of truth.
- Preserve unknown JSON fields.
- Use versionless arXiv IDs as stable record IDs; retain version in `source.version`.
- Do not overwrite `paper.pdf` unless explicitly refreshing the paper.
- Do not permanently delete paper directories; move them to `.trash/`.
- Send machine-readable output to stdout and diagnostics to stderr.
- Check the command exit code before assuming a write succeeded.

The full language-neutral format is in `SPEC.md`; JSON validation is in
`schema/paper.schema.json`.
