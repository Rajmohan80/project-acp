"""
AbhavTech Agentic Control Plane — WxCC corpus client.
LAB PROTOTYPE — not production ready.

Owns ACP's own path to the WxCC SLM corpus in Qdrant Cloud.
Mirrors the retrieval contract of the SLM's query_engine.retrieve EXACTLY:
  - embed with sentence-transformers "BAAI/bge-m3", normalize_embeddings=True
  - filter active=true
  - query_points, read .points / hit.score
  - rank Tier 1 above Tier 2, then by cosine score
Returns PLAIN DICTS (never dataclass objects) so results are trivially
JSON/msgpack-serialisable downstream.

Fails loudly ([ACP] MISSING: X) if Qdrant credentials are absent —
matching the config.py philosophy, without forcing those vars to be
required at Phase-0 startup.
"""

from __future__ import annotations

import os

from src.core.common.config import get_settings
from src.core.common.logging import get_logger

log = get_logger(__name__)

EMBED_MODEL = "BAAI/bge-m3"          # must match SLM query_engine.py exactly
RERANK_TOP_K = 20                    # fetch more, re-rank, return caller's k
MAX_CHUNKS_PER_DOC = 3              # prevent flow-designer/analyzer dominance

# Lazy singletons — loaded once on first search.
_model = None
_client = None


def _require(value: str | None, var_name: str) -> str:
    """Fail loudly, in the config.py [ACP] MISSING style, for domain creds
    that are Optional in config but required to reach the corpus."""
    if not value or not str(value).strip():
        raise RuntimeError(
            f"\n\n  [ACP] MISSING: {var_name}\n"
            f"  search_wxcc_corpus needs {var_name} to reach the WxCC corpus.\n"
            f"  Set it in D:\\project-acp\\.env (see .env.example).\n"
        )
    return value


def _get_model():
    """Load BGE-M3 once. Reads from HF_HOME cache (D:\\hf_cache) so the
    ~2GB model is NOT re-downloaded."""
    global _model
    if _model is None:
        settings = get_settings()
        if settings.hf_home:
            # Set before importing/constructing the model so the cache is used.
            os.environ.setdefault("HF_HOME", settings.hf_home)
        from sentence_transformers import SentenceTransformer
        log.info("bge_m3_loading", model=EMBED_MODEL,
                 hf_home=os.environ.get("HF_HOME"))
        _model = SentenceTransformer(EMBED_MODEL)
        log.info("bge_m3_loaded")
    return _model


def _get_client():
    """Construct the Qdrant client once, from ACP settings."""
    global _client
    if _client is None:
        settings = get_settings()
        url = _require(settings.qdrant_url, "QDRANT_URL")
        key = _require(settings.qdrant_api_key, "QDRANT_API_KEY")
        from qdrant_client import QdrantClient
        _client = QdrantClient(url=url, api_key=key)
        log.info("qdrant_client_ready",
                 collection=settings.qdrant_collection)
    return _client


def search(query: str, k: int = 5) -> list[dict]:
    """
    Embed the query with BGE-M3 and retrieve top-k chunks from the
    WxCC corpus. Returns a list of PLAIN DICTS, best first.

    Each dict:
        text, doc_id, filename, source_url, provenance_tier,
        priority, score, chunk_index, folder

    Mirrors SLM query_engine.retrieve so ACP scores identically.
    """
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    settings = get_settings()
    collection = settings.qdrant_collection

    model = _get_model()
    client = _get_client()

    # --- embed (normalize_embeddings=True — MUST match SLM) -------------
    vec = model.encode(query, normalize_embeddings=True).tolist()

    # --- filter: active=true only --------------------------------------
    must = [FieldCondition(key="active", match=MatchValue(value=True))]

    # --- vector search -------------------------------------------------
    result = client.query_points(
        collection_name=collection,
        query=vec,
        limit=RERANK_TOP_K,
        query_filter=Filter(must=must),
        with_payload=True,
    )

    # --- build plain dicts (NOT dataclasses) ---------------------------
    chunks: list[dict] = []
    for h in result.points:
        p = h.payload or {}
        chunks.append({
            "text":            p.get("text", ""),
            "doc_id":          p.get("doc_id", ""),
            "filename":        p.get("filename", ""),
            "source_url":      p.get("source_url", ""),
            "provenance_tier": p.get("provenance_tier", 2),
            "priority":        p.get("priority", ""),
            "score":           h.score,
            "chunk_index":     p.get("chunk_index", 0),
            "folder":          p.get("folder", ""),
        })

    # --- per-doc cap ---------------------------------------------------
    doc_counts: dict[str, int] = {}
    capped: list[dict] = []
    for c in chunks:
        fn = c["filename"]
        doc_counts[fn] = doc_counts.get(fn, 0)
        if doc_counts[fn] < MAX_CHUNKS_PER_DOC:
            capped.append(c)
            doc_counts[fn] += 1

    # --- re-rank: Tier 1 first, then cosine score ----------------------
    ranked = sorted(capped, key=lambda c: (c["provenance_tier"], -c["score"]))

    log.info("wxcc_search_done",
             returned=min(k, len(ranked)), retrieved=len(chunks))
    return ranked[:k]
