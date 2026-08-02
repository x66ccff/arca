# Arca

Arca is a portable, filesystem-native paper library built for humans and agents.
The folder is the database. The CLI is only a reference client.

## Why this shape

- **Portable:** zip or copy the whole `library/` directory.
- **Language-neutral:** canonical data is UTF-8 JSON, Markdown, and PDF.
- **Agent-friendly:** stable JSON/JSONL output, deterministic paths, explicit exit codes.
- **Human-friendly:** one directory per paper; notes are ordinary Markdown.
- **No service required:** no SQLite, server, account, framework, or package install.

Python 3.9+ is needed only for the bundled `arca` CLI. Any language can work
directly with the files described in `SPEC.md`.

The repository contains no personal library, private notes, or bundled PDFs.
`examples/demo-library/` is a metadata-only public demo with ten classic
machine-learning papers from 2012–2017. Run
`./arca init my-library` to create a fresh private library anywhere on disk.

## Five-minute start

```bash
./arca init library
./arca --library library add 2203.11171
./arca --library library list
./arca --library library search "self consistency" --jsonl
./arca --library library update 2203.11171 --status key --add-tag reasoning
./arca --library library note 2203.11171 "Canonical same-model ensemble baseline."
./arca --library library annotate 2203.11171 --page 7 --quote "..." --comment "Key ablation"
./arca --library library link 2203.11171 extends 2201.11903 --note "Samples multiple CoT paths"
./arca --library library neighbors 2203.11171 --depth 2 --json
./arca --library library visualize
./arca --library library doctor
```

By default `add` fetches arXiv metadata and the PDF. Use `--no-pdf` only when
you intentionally want a metadata-only record. Existing PDFs are never
overwritten unless `--refresh` is supplied.

## Public demo library

The metadata-only demo intentionally contains no PDF files:

- `1207.0580` — Dropout
- `1312.5602` — Deep Q-Networks (DQN)
- `1406.2661` — Generative Adversarial Networks (GANs)
- `1412.6980` — Adam
- `1502.03167` — Batch Normalization
- `1506.02640` — YOLO
- `1512.03385` — ResNet
- `1602.01783` — Asynchronous Advantage Actor-Critic (A3C)
- `1703.10593` — CycleGAN
- `1707.06347` — Proximal Policy Optimization (PPO)

Inspect or visualize it without changing the repository:

```bash
./arca --library examples/demo-library list
./arca --library examples/demo-library search "residual" --jsonl
./arca --library examples/demo-library visualize /tmp/arca-demo.html --force
```

To keep local PDFs, create your own library and add the examples normally:

```bash
./arca init my-library
./arca --library my-library add 1406.2661
./arca --library my-library add 1512.03385
./arca --library my-library add 1707.06347
```

## Folder layout

```text
library/
├── manifest.json
├── papers/
│   └── 2203.11171/
│       ├── metadata.json   # canonical structured record
│       ├── notes/
│       │   ├── summary.md       # free-form human/agent notes
│       │   └── annotations.jsonl # page, quote, comment, tags
│       └── paper.pdf       # original PDF bytes
├── graph/
│   └── edges.jsonl         # canonical paper-to-paper relations
├── _index/
│   ├── catalog.jsonl       # generated; safe to delete/rebuild
│   └── paper-graph.html    # generated interactive visualization
├── .staging/               # transactional imports
└── .trash/                 # recoverable removals
```

Only `papers/*/metadata.json`, `notes/`, stored files, and
`graph/edges.jsonl` are canonical. `_index/catalog.jsonl` is a disposable
acceleration layer.

## Agent-oriented commands

Every read command supports machine output:

```bash
./arca --library library list --json
./arca --library library list --jsonl
./arca --library library get 2203.11171 --json
./arca --library library search "verifier" --jsonl
./arca --library library path 2203.11171
```

Diagnostics go to stderr; structured data goes to stdout. A non-zero exit code
means the requested operation did not complete.

For bulk or non-Python workflows, write records following
`schema/paper.schema.json`, place them under `papers/<key>/`, then run:

```bash
./arca --library library reindex
./arca --library library doctor
```

You can also ingest a local metadata file and PDF atomically:

```bash
./arca --library library ingest record.json --pdf downloaded-paper.pdf
```

## Default visualization

Generate the built-in interactive paper graph with one command:

```bash
./arca --library library citation-sync
./arca --library library visualize
```

`citation-sync` uses the free Semantic Scholar API and stores the result inside
the library folder; visualization itself remains offline.

The default output is `library/_index/paper-graph.html`. It is a standalone,
offline HTML file: D3 is embedded, so opening the page does not require a
server, package manager, or network connection. Solid directed edges are
citations read from the portable `_index/citation-cache.json` cache. Dashed
undirected edges are title-and-abstract similarity relations (title-weighted
TF-IDF cosine; up to four nearest neighbors per paper, minimum similarity 0.05).
If the same pair has both relations, the citation edge takes precedence. The
dashed-edge force is intentionally much weaker than citation force (`0.065`
versus `0.46`). Stored manual edges and chat history do not create displayed
connections. Node color denotes the primary collection; older papers are more
transparent, newer papers are more opaque, and node diameter grows with total
displayed degree. Nodes can be dragged, the canvas can be panned or zoomed, and
clicking a node highlights its neighbors by relation type. Labels use semantic
zoom like a map: the overview shows only high-degree hubs, zooming in reveals
progressively more arXiv IDs, and deeper zoom adds shortened paper titles.

Render a neighborhood or choose an output path:

```bash
./arca --library library visualize --center 2203.11171 --depth 2
./arca --library library visualize ./my-paper-graph.html --force
```

The HTML is generated state, not canonical library data, and can be deleted or
rebuilt at any time. The template is `templates/default-visualization.html`.

## Safety model

- Writes use a temporary file followed by atomic replacement.
- New imports are assembled in `.staging/` before becoming visible.
- `remove` moves a paper to `.trash/`; it does not erase it.
- Existing PDFs are not overwritten without `--refresh`.
- Downloads must begin with `%PDF-` and be larger than 10 KiB.
- SHA-256 and byte size are stored and checked by `doctor`.

## Useful commands

```text
init PATH                         create a library
add ARXIV_ID_OR_URL               fetch metadata and PDF
ingest METADATA_JSON [--pdf PDF]  add local files atomically
list / get / search / path        query records
update ID                         change status, title, or tags
note ID TEXT                      append timestamped Markdown note
annotate ID                       add a page/quote/comment annotation
link / unlink / neighbors         edit and query paper relationships
graph --format json|jsonl|dot     export the paper graph
citation-sync                     refresh the free citation cache
visualize [OUTPUT]                generate the default offline HTML graph
remove ID --yes                   move to trash
restore ID                        restore newest matching trash entry
reindex                           rebuild catalog.jsonl
doctor [--full]                   validate structure and checksums
```

## Status vocabulary

`inbox`, `reading`, `key`, `archived`. Custom tags and collections remain open
strings, so the format does not impose a research taxonomy.

## License

Arca is released under the MIT License. The bundled D3 distribution retains its
own license in `vendor/D3-LICENSE.txt`. Paper metadata remains attributable to
its original sources; the demo does not redistribute paper PDFs.
