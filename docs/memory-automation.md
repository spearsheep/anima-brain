# Memory maintenance and embedded management

This release completes the local scheduling path. It is not a claim of cloud-scale hosting
or of automatic access to a ChatGPT conversation.

## Data flow

1. The host calls `prepare_turn` and `commit_turn` with the actual exchange. The commit saves
   original evidence and quoted fact proposals atomically. `automatic` permits host-authored
   fact extraction; it does not intercept messages or force the host to call a tool.
2. Committed evidence without a vector or maintenance marker is the durable backlog. There
   is no vulnerable commit-then-enqueue gap. Notes invalidate stale vectors.
3. A policy-controlled worker claims one maintenance job per character across local processes.
   `companion http` and `companion serve` start it; SDK users use
   `with runtime.automation.worker(): ...`, or run `companion --db PATH worker`.
4. Embedding handles up to 32 excerpts per job. Summary maintenance handles at most eight
   excerpts (normally four turns), creates grounded notes and cited episode/core documents.
   It runs when pending turns reach the configured threshold, pending text reaches 12,000
   characters, or the newest pending evidence is idle for 300 seconds. Batch bounds remain
   fixed even with a larger threshold. Old evidence is retained. Current fact revisions
   override old sources, and a concurrent fact edit invalidates the in-flight summary.
5. Optional semantic retrieval enriches `prepare_turn` using lexical + cosine reciprocal
   rank fusion. Query embeddings are journaled per turn and model namespace. Replaying a
   pending turn does not rebill its query. Provider failure returns explicit lexical fallback.
   The existing bounded reader may perform additional targeted searches when configured.

## Configuration

Use the SDK's memory policy or ask the host to call `configure_memory_automation`
after authorizing provider use:

```json
{
  "character_id": "luna",
  "policy": {
    "embedding": true,
    "summaries": false,
    "host_summaries": true,
    "semantic_retrieval": true,
    "summary_turns": 4,
    "summary_chars": 12000,
    "idle_seconds": 300,
    "daily_jobs": 100
  }
}
```

For characters without an explicit policy, embedding, semantic retrieval and host summaries
default on; paid background summaries default off. Existing explicit off settings remain off.
Once an embedding provider is configured, indexing can process previously saved history and
incur API fees. Host summaries require the active host to call the summary tools. Policies persist in the same SQLite database and are shared by MCP
and SDK/API clients. Memory mode `off` pauses worker processing. Disabling a switch prevents new
jobs; it does not cancel a provider request already in flight.

Provider settings stay in the existing private local provider configuration, never in MCP
responses. Embedding uses its configured endpoint/model/key. Autonomous summaries need a
separately configured chat/summary model; the ChatGPT subscription cannot run backend jobs.
Missing configuration is reported and does not repeatedly attempt calls. Existing running
processes need restart after provider configuration is saved from another process.

The daily cap is a rolling 24-hour **job count**, not a dollar budget. One summary job may
contain up to eight note calls plus one consolidation call. Chat/query-embedding and manual
operations are separate. Usage is journaled; unavailable token prices are not treated as zero.

## Recovery and correctness

A worker renews its lease while making bounded provider requests. Another process cannot
claim work for that character. A dead lease or provider/validation failure moves the job to
`review` and stops automatic maintenance for that character. There are no blind paid retries.
After inspecting receipts, the user can explicitly acknowledge the job with
`retry_memory_job`. This permits a new attempt, which may incur another charge. Pending work
survives restart. Successfully stored vectors/processed batches are not resubmitted.

SQLite serializes reservations/writes; network calls run outside transactions. Manual and
automatic index/maintenance operations share an operation reservation check. Host-authored
annotations and fact edits remain possible; revision/source checks reject stale derived writes.

## Optional MCP memory card

`show_memory_panel` renders a bundled MCP Apps component: paginated facts (50 per page),
latest eight core/episode documents, citation expansion, and actual maintenance status.
Editing/deleting uses app-visible revision-checked tools. Concurrent edits fail instead of
silently overwriting. Delete requires a second confirmation in the component. Original chat
is retained; cached summaries are cleared. This is fact deletion, not erasure of the original
information from all history, backups or model context.

Providers must be configured locally. Clients without MCP Apps can use the ordinary
inspection tools; the engine does not require the embedded UI.

## Scale boundary

Appropriate for a local owner with multiple characters and multiple local clients. No load-test
capacity claim is made. Exact vector retrieval currently scans this character's vectors:
O(number of vectors × dimensions), though only bounded top results are retained. Large corpora
need an indexed vector backend. Multi-user hosting additionally needs authenticated tenant
binding, a server database, independent workers, quotas, backups and operational monitoring.
The interfaces separate tools/UI, orchestration, storage and providers; the storage code is
still SQLite-specific and migrating it requires implementation, not just an environment flag.

## Summaries by ChatGPT / another MCP host

The user can choose `configure_host_summaries(character_id, enabled=true)`. This enables
`host_summaries` and disables paid background summaries, preserving all embedding settings.
Both summary writers cannot be enabled simultaneously. No backend reply-model key is needed.
Prepare/commit responses include a due notice based on the same turn/text/idle thresholds.
The host reads `prepare_memory_summary`, authors episode/core with supplied original citations,
and calls `commit_memory_summary`. Snapshot checks reject changed facts/core/batches; exact
retries are idempotent. Originals, summaries, completion markers and receipts remain local.
The host can optionally add contextual retrieval notes using `annotate_evidence`.

At most one bounded batch per conversational turn is recommended. This is a tool workflow,
not a guarantee that every host will follow it. It runs only when the host is active and calls
the tools; an idle threshold does not wake ChatGPT. It uses host context/usage but makes no
backend summary-model request. Embeddings remain separate and may still cost money if enabled.
The SDK's reply model does not automatically act as this MCP host.
