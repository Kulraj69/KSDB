# Next Steps

Last updated: 2026-05-07.

## Implemented In This Pass

The next best small improvement was query explainability. KSdb now has:

- `POST /collections/{name}/query/explain`
- `Collection.explain_query(...)`
- Cloud API/client support for the same explain flow
- Per-result `matched_by`, `vector_rank`, `vector_distance`, `keyword_rank`, and `rrf_score`
- Query profile data with candidate counts and timings

This helps answer practical retrieval questions:

- Did this result rank because of semantic similarity, keyword match, or both?
- Did a metadata filter remove most candidates?
- Is time going into embedding, vector search, FTS, or fusion?
- Are there enough keyword candidates to justify tuning FTS?

## Recommended Next Sprint

1. Add `where_document` filters.
   Text filters let users require or exclude terms before final fusion, which is important for logs, legal/policy search, and exact product identifiers.

2. Add MMR diversity selection.
   RAG contexts often contain near-duplicate chunks. MMR can keep the top result relevant while making the remaining context more diverse.

3. Add backup, restore, and rebuild commands.
   Local users need a safe way to snapshot `.ksdb/metadata.db` plus `.ksdb/indices/`, and production users need a predictable rebuild path after deletes or index corruption.

4. Add a retrieval evaluation script.
   A small JSONL fixture with queries, expected IDs, and latency output will make future search changes measurable instead of vibes-based.

5. Align the legacy `server/` folder or remove it.
   The package server is now the source of truth. Keeping a second server implementation will keep creating drift unless it is intentionally marked legacy.

## Suggested Order

Start with `where_document`, then MMR, then backup/rebuild. Those three make the product feel more reliable without expanding the system too much.

For each search-quality change, use `explain_query()` before and after the change and record:

- vector candidates
- keyword candidates
- fused candidates
- result ranks
- latency by stage
