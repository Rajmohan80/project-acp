# AbhavTech — Environment Reference

**Last updated:** 30 July 2026 — written after Block 1 validation
**Purpose:** Stop the interpreter-hunt problem. Every session starts here.

---

## The Six-Python Problem

This machine has six Python installations registered with the `py` launcher:

| Version | Path | Role |
|---|---|---|
| **3.14** | `C:\Users\Abhav\AppData\Local\Programs\Python\Python314\python.exe` | **SLM runtime** — qdrant-client + sentence-transformers installed here (no venv) |
| 3.13 | `C:\Users\Abhav\AppData\Local\Programs\Python\Python313\python.exe` | Unused by either project |
| **3.11** | `C:\Users\Abhav\AppData\Local\Programs\Python\Python311\python.exe` | **ACP venv base** — `D:\project-acp\.venv` built on this interpreter |
| 3.10 | `D:\Python-new installation\python.exe` | Unused by either project |
| 3.9 | `C:\Program Files (x86)\Microsoft Visual Studio\Shared\Python39_64\python.exe` | Visual Studio only |
| 3.7 | `C:\Program Files (x86)\Microsoft Visual Studio\Shared\Python37_64\python.exe` | Visual Studio only |

**The failure mode:** opening a terminal and running `python` or `pip` without activating
a venv resolves to whichever interpreter is first on PATH — which may be none of the above.
Always activate the correct venv before doing anything.

---

## Project: WxCC SLM — `D:\project-slm-webex\`

| Item | Value |
|---|---|
| **Python interpreter** | `C:\Users\Abhav\AppData\Local\Programs\Python\Python314\python.exe` |
| **Venv** | None — packages installed globally into Python 3.14 |
| **Key packages** | `qdrant-client`, `sentence-transformers`, `langchain`, `fastapi`, `groq` |
| **How to run** | `cd D:\project-slm-webex` then `python api_server.py` (Python 3.14 resolves via PATH) |
| **Env file** | `D:\project-slm-webex\.env` — loaded at startup via `load_dotenv()` in `api_server.py` |
| **Key env vars** | `QDRANT_URL`, `QDRANT_KEY` (note: `_KEY`, not `_API_KEY`), `GROQ_API_KEY` |
| **HF cache** | `D:\hf_cache` — BGE-M3 (~2.27 GB) cached here. Do NOT delete or re-download. |

**Verify SLM environment is working:**
```
"C:\Users\Abhav\AppData\Local\Programs\Python\Python314\python.exe" -c "import qdrant_client, sentence_transformers; print('SLM env OK')"
```

---

## Project: ACP — `D:\project-acp\`

| Item | Value |
|---|---|
| **Python interpreter** | `C:\Users\Abhav\AppData\Local\Programs\Python\Python311\python.exe` |
| **Venv** | `D:\project-acp\.venv` — always activate before running anything |
| **Key packages** | `fastmcp`, `fastapi`, `uvicorn`, `qdrant-client`, `sentence-transformers`, `tinydb`, `python-jose`, `structlog` |
| **How to activate** | `cd D:\project-acp` then `.venv\Scripts\activate` — prompt shows `(.venv) D:\project-acp>` |
| **Env file** | `D:\project-acp\.env` — loaded at import time via `load_dotenv()` in `config.py` |
| **Key env vars** | `OAUTH_SECRET_KEY`, `QDRANT_URL`, `QDRANT_API_KEY` (note: `_API_KEY`, not `_KEY`), `QDRANT_COLLECTION`, `HF_HOME` |
| **Ports** | OAuth issuer: 9000 — MCP server: 8100 |

**Every ACP session starts with:**
```
cd D:\project-acp
.venv\Scripts\activate
```
Confirm prompt shows `(.venv) D:\project-acp>` before running anything.

**Verify ACP environment is working:**
```
python -c "import qdrant_client, sentence_transformers, fastmcp, tinydb; print('ACP env OK')"
```

---

## Qdrant Cloud

| Item | Value |
|---|---|
| **Cluster name** | SLM-FOR-WEBEX |
| **Collection** | `wxcc_slm_corpus` |
| **Cluster URL** | `https://97eedd23-c450-4cdf-94d3-66757dc03b90.australia-southeast1-0.gcp.cloud.qdrant.io:6333` |
| **Region** | australia-southeast1 (GCP) |
| **Chunks** | 2,633 |
| **Vector size** | 1024 (BGE-M3) |
| **Distance** | Cosine |
| **Filter** | Always filter `active=true` — superseded chunks stay in collection with `active=false` |

**Credential name split (important):**

| Project | Env var name | Points to |
|---|---|---|
| WxCC SLM | `QDRANT_KEY` | Same Qdrant API key |
| ACP | `QDRANT_API_KEY` | Same Qdrant API key |

Same secret, different variable names. Both `.env` files must be kept in sync when the key rotates.

**Verify collection from ACP venv:**
```
(.venv) D:\project-acp> python -c "
from dotenv import load_dotenv; load_dotenv('.env')
import os
from qdrant_client import QdrantClient
c = QdrantClient(url=os.environ['QDRANT_URL'], api_key=os.environ['QDRANT_API_KEY'])
v = c.get_collection('wxcc_slm_corpus').config.params.vectors
print(f'size={v.size} distance={v.distance}')
"
```
Expected: `size=1024 distance=Distance.COSINE`

---

## BGE-M3 Model Cache

| Item | Value |
|---|---|
| **Model** | `BAAI/bge-m3` |
| **Cache path** | `D:\hf_cache` |
| **Size** | ~2.27 GB |
| **Set via** | `HF_HOME=D:\hf_cache` in ACP `.env`; `os.environ.setdefault("HF_HOME", ...)` in SLM `query_engine.py` |

**NEVER delete `D:\hf_cache`.** Re-downloading BGE-M3 takes 20+ minutes and consumes ~2.27 GB.

Both projects load from the same cache. ACP's `corpus_client.py` reads `HF_HOME` from
`get_settings().hf_home` before constructing the `SentenceTransformer`.

---

## Git State (as of Block 1)

| Commit | Message |
|---|---|
| `212dec2` | Phase 1 Block 1 Track C: search_wxcc_corpus governed tool wired to wxcc_slm_corpus |
| `52cfb69` | Phase 0 COMPLETE: all 10 gate checks passed — ready for Phase 1 |
| `c5224de` | Phase 0 Block 9: naming-map.md + LAB PROTOTYPE disclaimers on all __init__.py |

**Never commit `.env`** — it is in `.gitignore`. Confirm with `git status` before every commit.

---

## Quick Diagnostic — When Things Break

**"ModuleNotFoundError: No module named X" in ACP:**
→ Venv not activated. Run `.venv\Scripts\activate` first.

**"[ACP] MISSING: QDRANT_URL" or similar:**
→ `.env` file has the var commented out (`# QDRANT_URL=`) or missing entirely.
→ Open `D:\project-acp\.env`, remove the `#`, save, re-run.

**"QDRANT_URL not found" in SLM:**
→ `D:\project-slm-webex\.env` missing the var, or `load_dotenv()` not called before import.
→ The SLM loads `.env` automatically at `api_server.py` startup — manual one-liners must call
  `load_dotenv(r'D:\project-slm-webex\.env')` explicitly.

**"can't open file scripts\demo_wxcc.py":**
→ Wrong directory. Run `cd D:\project-acp` first.

**BGE-M3 re-downloading despite cache:**
→ `HF_HOME` not set before `SentenceTransformer()` is constructed.
→ ACP: check `HF_HOME=D:\hf_cache` is in `.env` and `hf_home` field is in `config.py`.
→ SLM: `query_engine.py` sets `os.environ.setdefault("HF_HOME", ...)` before model load.

---

*AbhavTech Consulting | Rajmohan Mangattu | CCIE Collaboration #55207*
*Document written from working lab — not ahead of it.*
