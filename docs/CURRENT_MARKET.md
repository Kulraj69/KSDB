# What Is Happening Now

Last reviewed: 2026-05-07.

Vector databases are no longer judged by vector search alone. The active market is moving toward hybrid retrieval, better metadata filtering, reranking/diversity controls, agent-facing APIs, and operational features such as backups, monitoring, governance, and local development emulators.

## Current Signals

- Hybrid retrieval is the baseline. TechTarget reported on 2026-04-14 that enterprise AI search increasingly needs semantic similarity plus exact keyword precision, especially for product names, acronyms, customer identifiers, error codes, and policy language: https://www.techtarget.com/searchdatamanagement/feature/Hybrid-search-demands-reshape-retrieval-frameworks-for-AI
- PostgreSQL/pgvector is improving filtered ANN behavior. pgvector 0.8.0 added iterative index scans to reduce "overfiltering" when ANN search and `WHERE` filters interact: https://www.postgresql.org/about/news/pgvector-080-released-2952/
- Qdrant is positioning around dense+sparse hybrid search, advanced metadata filtering, one-stage filtering during HNSW traversal, reranking, quantization, and deployment control: https://qdrant.tech/
- Chroma Cloud now presents itself as a search and retrieval platform with vector, sparse vector, lexical BM25/SPLADE, full-text, trigram, regex, metadata search, forking, and multi-language clients: https://landing.trychroma.com/
- Pinecone's 2026 release notes show production platform work around fetch-by-metadata, dedicated read nodes, MCP servers, sparse vectors, backups/restore, local development, Prometheus monitoring, audit logs, and data import: https://docs.pinecone.io/release-notes/2026
- Weaviate 1.37, released 2026-04-23, added preview MCP support, extensible tokenizers, MMR diversity search, query profiling, and incremental backups: https://weaviate.io/blog/weaviate-1-37-release
- Milvus' roadmap points toward multimodal data, hot/cold tiering, text/blob storage, distributed UDFs, scalar query optimization, dynamic sharding, and Vector Lake architecture: https://blog.milvus.io/docs/roadmap.md

## What This Means For KSdb

KSdb should lean into a focused open-source position:

- Be easy to run locally with a Chroma-like Python API.
- Make hybrid retrieval correct and understandable before adding more knobs.
- Treat metadata filtering as a first-class retrieval feature, not an afterthought.
- Add real-world ingestion examples so users can test current, messy data quickly.
- Build observability and evaluation into the developer loop early.

## Competitive Gaps To Close

- Filter pushdown: current correctness is handled before ranking, but large collections need filter-aware ANN traversal or partitioned indexes.
- Reranking: add optional reranking and MMR so RAG contexts are relevant without being repetitive.
- Query profiling: expose vector time, FTS time, filter candidate counts, and final fusion behavior.
- Operational safety: add backups, restore, index rebuild, migration checks, and clearer Postgres/S3 production paths.
- Agent integration: harden MCP support and document safe read-only/write modes.
