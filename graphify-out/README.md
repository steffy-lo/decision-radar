# Using Graphify in this repository

Graphify builds a navigable map of the code, design documents, and other supported project files. Graph artifacts describe the branch and commit from which they were generated; they do not represent every branch at once.

## Keep the graph aligned with a branch

The repository has Graphify `post-commit` and `post-checkout` hooks installed. The commit hook launches an asynchronous code-only rebuild after commits; the checkout hook launches a code-only rebuild when switching branches. These hooks keep code relationships fresh, but they do not semantically re-extract docs, papers, or images. Since they run in the background, check the log before inspecting or committing their output:

```bash
tail -f ~/.cache/graphify-rebuild.log
```

For the shared `main` graph, switch to `main` and pull. The checkout hook will rebuild the code graph for the branch:

```bash
git switch main
git pull --ff-only
```

If you need to refresh manually, `graphify update .` incrementally refreshes code structure without LLM/API cost. It is also useful after a hook failure. If the branch switch includes large refactors or deleted files and the graph retains stale nodes, rebuild with:

```bash
graphify extract . --force
```

For changes to design docs, papers, or images, run a full extraction so semantic relationships are refreshed; the hooks do not handle these files:

```bash
graphify extract .
```

Semantic extraction may need a configured Graphify LLM backend. You can inspect the extraction options with `graphify extract --help`. To avoid an LLM pass when only code matters, use `graphify extract . --code-only`.

The hooks rebuild `graph.json` and `GRAPH_REPORT.md`; regenerate `graph.html` when you want the visualization to match, with `graphify export html`. Inspect the results before sharing them. Hook output is created after the commit has already completed, so stage and commit the generated graph changes in a follow-up commit if the team tracks graph artifacts. If you work on a feature branch, the checkout hook rebuilds the code graph for that branch when you switch to it; regenerate or review on `main` before treating the files as the shared `main` graph.

## Ask useful questions

Start with a focused question that names a component or behavior. Graphify expands it through related nodes and source files:

```bash
graphify query "How does project membership authorization work?"
graphify path "authenticate_bearer()" "getCurrentProjectMembership()"
graphify explain "Transactional Outbox"
graphify affected "EvidenceValidator"
```

Use `query` to explore a flow, `path` to find the shortest connection between two concepts, `explain` to inspect a node and its neighbors, and `affected` to see downstream impact. When a result is too broad, narrow it with a specific symbol, route, service, or design concept. Use `--budget N` to limit query output.

Treat graph results as a navigation aid, then verify important claims in the cited source files. Generated relationships can be incomplete or ambiguous, especially across languages or where a connection is inferred. `GRAPH_REPORT.md` gives a wider architectural overview; `graph.html` is useful for visual exploration.

## What to share

Useful generated artifacts are:

- `graph.json`: graph data used by Graphify commands.
- `GRAPH_REPORT.md`: community overview, hubs, and notable connections.
- `graph.html`: interactive visualization.
- `.graphify_labels.json`: curated community names used by exports.

The cache, cost tracker, manifest, and local interpreter marker support local extraction. They are not needed to query a shared graph and should generally remain local. In particular, avoid committing machine-specific `.graphify_python` and `.graphify_root` files.
