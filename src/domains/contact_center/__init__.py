"""
AbhavTech Agentic Control Plane — Track C: Contact Center domain.
LAB PROTOTYPE — not production ready.

First real domain module. Wires the existing WxCC SLM corpus
(Qdrant collection 'wxcc_slm_corpus', BGE-M3 / 1024-dim / Cosine)
into ACP as a governed MCP tool: search_wxcc_corpus.

The corpus is READ-ONLY from ACP's perspective. This module owns its
own path to Qdrant (own client, own embedder) — it does not import from
or run under the SLM project. The two projects share the collection,
not the interpreter.
"""
