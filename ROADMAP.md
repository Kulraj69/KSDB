# KSdb Roadmap

Last updated: 2026-05-07.

## Recently Updated

- Fixed server startup when graph extraction is enabled.
- Made local storage honor `KSDB_DATA_PATH` / `ksdb run --path`.
- Added `--data-dir` as a CLI alias for the documented data directory flag.
- Indexed single-document inserts into SQLite FTS so hybrid search works consistently.
- Hardened FTS queries for terms like `X-99`.
- Added batch input validation.
- Added document delete support to the REST API and Python client.
- Improved filtered query correctness by preselecting matching metadata IDs before fusion.
- Added `query/explain` and `explain_query()` for hybrid ranking diagnostics.
- Added a live Hacker News ingestion example for current public data.
- Added fresh usage and market context docs.

## Next: 0.2 Retrieval Quality

- Add `where_document` support for text-level filters.
- Add optional BM25/FTS score exposure alongside the current vector rank, keyword rank, and RRF profile.
- Tune RRF and expose `hybrid_alpha` or similar weighting.
- Add optional MMR diversity selection to reduce duplicate RAG context.
- Add optional cross-encoder reranking for top candidates.
- Add retrieval evaluation scripts with recall, MRR, nDCG, and latency metrics.

## 0.3 Operations

- Add backup and restore commands for SQLite metadata plus HNSW index files.
- Add index rebuild and compaction commands, including cleanup for deleted labels.
- Add database migration/version checks.
- Add structured logs and `/metrics` for Prometheus.
- Bring the Docker/server folder in line with the package server so local Docker and `ksdb run` expose the same API.
- Add Postgres full-text search support instead of SQLite-only FTS.

## 0.4 Scale And Tenancy

- Add filter-aware indexing or partition routing so filtered search does not need full-candidate scans.
- Add collection-level HNSW settings such as `M`, `ef_construction`, and query `ef`.
- Add multi-tenant isolation with API keys, quotas, and audit logs.
- Add background ingestion jobs for PDFs, OCR, graph extraction, and external connectors.
- Add S3 index consistency checks and retryable uploads.

## 0.5 Product And Ecosystem

- Add a small dashboard for collections, documents, query testing, and graph inspection.
- Publish LangChain and LlamaIndex integration examples that run end to end.
- Harden MCP server support for safe agent memory workflows.
- Add TypeScript client coverage.
- Publish reproducible benchmarks against Chroma, Qdrant, pgvector, and Weaviate with hardware and dataset details.
