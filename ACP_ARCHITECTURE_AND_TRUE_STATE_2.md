# AbhavTech — ACP Architecture & True State
**Rajmohan Mangattu | CCIE Collaboration #55207 | AbhavTech Consulting**
**Date: 31 July 2026 | Session 2 debrief — Track C Block 1 + Track N Blocks 2-4**

---

## 1. What Was Built This Session

### Track C — Block 1: `search_wxcc_corpus`
**Commit:** `212dec2`

First real governed domain tool. Wires the existing WxCC SLM corpus
(Qdrant Cloud, `wxcc_slm_corpus`, 2,633 chunks, BGE-M3/1024-dim/Cosine)
into ACP as a governed MCP tool.

**Validated output (UAE residency query):**
```
[4] workbook_b_B12_-_Data_Locality_Matrix.md (Tier 1, score=0.606)
    Data Centre: SG1-served: UAE | Country / Territory Served: United Arab Emirates
    In-Country Residency?: NO — tenant data rests in Singapore
    Applicable Law: UAE PDPL (Federal Decree-Law 45/2021); CBUAE rules for financial sector
    Design Action: FLAGSHIP-SCENARIO RULE: disclose Singapore DC immediately
```

---

### Track N — Block 2: `describe_topology`
**Commit:** `c066a0c`

First network domain tool. Returns nodes, links, sites, role breakdown,
and SD-WAN edge summary for a named topology.

**Validated output:**
```
topology       : sample_sdwan_branch
description    : AbhavTech lab — SD-WAN fabric with HQ 3-tier LAN and single Mumbai branch
platform       : Cisco SD-WAN (Viptela / IOS-XE)
sites (3)      : controllers, hq, branch-mumbai
nodes          : 9
links          : 11

Role breakdown:
  access                2
  core                  1
  distribution          1
  sd-wan-controller     2
  sd-wan-edge           2
  sd-wan-orchestrator   1

SD-WAN edges:
  HQ-cEdge-01      sd_wan_role=hub    transports=[mpls, internet]  site=hq
  Branch-cEdge-01  sd_wan_role=spoke  transports=[mpls, internet]  site=branch-mumbai
```

---

### Track N — Block 3: `find_path`
**Commit:** `2f8ff0e`

BFS shortest-hop path finding between any two nodes in the topology.
Uses `diagnostics:run` scope — different from `describe_topology` —
proving ACP enforces granular scope control across tool types.

**Validated output (branch-sw-01 → hq-core-sw-01):**
```
found          : True
hops           : 3
link types     : lan → omp-tunnel → lan

Path:
  START  Branch-SW-01
  HOP 1  Branch-cEdge-01   ← via lan
  HOP 2  HQ-cEdge-01       ← via omp-tunnel
  HOP 3  HQ-Core-SW-01     ← via lan
```

---

### Track N — Block 4: `check_device_role`
**Commit:** `807aaa9`

Returns role, site, platform, description, and all directly connected
peers for a named node. Complete device profile in one governed call.

**Validated output (hq-cedge-01):**
```
node           : HQ-cEdge-01
role           : sd-wan-edge
sd_wan_role    : hub
wan_transports : ['mpls', 'internet']
site           : hq
device_type    : cEdge
platform       : Cisco ISR4451 IOS-XE SD-WAN
description    : HQ hub edge — dual-transport (MPLS + internet),
                 terminates OMP tunnels from all spokes

Peers (5):
  vManage-01        via management
  vBond-01          via control
  vSmart-01         via control
  Branch-cEdge-01   via omp-tunnel
  HQ-Core-SW-01     via lan
```

---

## 2. Governance Proven This Session

Every tool call went through `_check_governance()` in `app.py`.
Six governance decisions validated in `demo_network.py`:

| Run | Tool | Token | Scope Required | Decision | Audit Reason |
|---|---|---|---|---|---|
| 1 | describe_topology | engineers | knowledge:read | ALLOWED | — |
| 2 | describe_topology | viewers | knowledge:read | REFUSED | TOOL_BLOCKED_IN_CONTROL_HUB |
| 3 | find_path | engineers | diagnostics:run | ALLOWED | — |
| 4 | find_path | viewers | diagnostics:run | REFUSED | TOOL_BLOCKED_IN_CONTROL_HUB |
| 5 | check_device_role | engineers | knowledge:read | ALLOWED | — |
| 6 | check_device_role | viewers | knowledge:read | REFUSED | TOOL_BLOCKED_IN_CONTROL_HUB |

All six lines written to `audit.readable.log`.

---

## 3. What Is Actually Built — Full File List

```
D:\project-acp\
  ENVIRONMENT.md                              ← six-Python split documented
  src/
    core/
      common/
        config.py                             ← added qdrant_collection, hf_home fields
        logging.py                            ← unchanged
      mcp/
        server/
          app.py                              ← echo + search_wxcc_corpus +
                                                 describe_topology + find_path +
                                                 check_device_role
        control_hub.yaml                      ← 7 tools registered
        oauth/
          issuer.py                           ← unchanged
        lifecycle/                            ← stub
        registry/                             ← stub
      audit/
        writer.py                             ← unchanged
      autonomy/                               ← stub
    domains/
      contact_center/
        __init__.py                           ← Track C docstring
        corpus_client.py                      ← BGE-M3 + Qdrant client
        tool.py                               ← run_search
      network/
        __init__.py                           ← Track N docstring
        topology_store.py                     ← get_topology, summarise,
                                                 build_graph, bfs_path, get_node
        tool.py                               ← run_describe_topology,
                                                 run_find_path,
                                                 run_check_device_role
        topologies/
          sample_sdwan_branch.json            ← 9 nodes, 11 links, 3 sites
    surfaces/                                 ← stubs
  scripts/
    demo_wxcc.py                              ← Track C validation
    demo_network.py                           ← Track N validation (6 runs)
    install.bat / run_oauth.bat / run_mcp.bat ← Phase 0 scripts
  .env                                        ← QDRANT_URL, QDRANT_API_KEY,
                                                 QDRANT_COLLECTION, HF_HOME set
  .env.example                                ← placeholders
```

---

## 4. Git Log

```
807aaa9  Phase 1 Block 4 Track N: check_device_role governed tool, Track N complete
2f8ff0e  Phase 1 Block 3 Track N: find_path governed tool, BFS path finding over SD-WAN topology
c066a0c  Phase 1 Block 2 Track N: describe_topology governed tool, SD-WAN branch topology
493b6ea  ENVIRONMENT.md: document six-Python split, interpreter paths, credential naming
212dec2  Phase 1 Block 1 Track C: search_wxcc_corpus governed tool wired to wxcc_slm_corpus
52cfb69  Phase 0 COMPLETE: all 10 gate checks passed — ready for Phase 1
```

---

## 5. Key Architecture Decisions Made This Session

**ACP owns its own Qdrant client path (Track C)**
ACP does not proxy through the SLM's FastAPI. It has its own
`qdrant-client` and `sentence-transformers` in its own 3.11 venv,
pointing at the same Qdrant collection. Clean boundary — ACP doesn't
depend on the SLM being alive.

**Governance injected, not imported**
`tool.py` in both Track C and Track N receives `check_governance`
as a function argument from `app.py`. No circular imports.
Pattern: `run_search(query, token, *, check_governance=_check_governance)`

**Static topology descriptor (Track N)**
Track N tools query JSON files, not live devices. This is correct
for a lab prototype — the data source is isolated in `topology_store.py`.
Swapping to live Catalyst Center API = one function change,
zero changes to governance or tool layer.

**Two scopes across three Track N tools**
- `describe_topology` → `knowledge:read`
- `find_path` → `diagnostics:run`
- `check_device_role` → `knowledge:read`
Proves ACP enforces granular scope control, not binary allow/block.

**LD-12 satisfied:** Track N is complete and committed.
Track C can now proceed further.

---

## 6. Environment Reference (summary — full detail in ENVIRONMENT.md)

| Item | Value |
|---|---|
| SLM interpreter | Python 3.14 — `C:\Users\Abhav\AppData\...\Python314\python.exe` |
| ACP venv | Python 3.11 — `D:\project-acp\.venv` |
| Qdrant cluster | `https://97eedd23-c450-4cdf-94d3-66757dc03b90.australia-southeast1-0.gcp.cloud.qdrant.io:6333` |
| Collection | `wxcc_slm_corpus` — 2,633 chunks, BGE-M3, 1024-dim, Cosine |
| BGE-M3 cache | `D:\hf_cache` — do NOT delete |
| SLM env var | `QDRANT_KEY` |
| ACP env var | `QDRANT_API_KEY` (same secret, different name) |

**Every ACP session starts with:**
```
cd D:\project-acp
.venv\Scripts\activate
```

---

## 7. What Is NOT Built Yet

| Item | Status |
|---|---|
| Block 5 — A2A boundary | Not started — next session |
| Network agent / LLM router | Not started — needed for Block 5 |
| n8n workflows (WxCC SLM) | Not started |
| PostgresSaver migration | Not started (MemorySaver in use) |
| Live device data source | Not started (static JSON today) |
| Portfolio demo video | Not recorded |
| LinkedIn update | Deferred — after A2A boundary demo |

---

## 8. Block 5 — What Comes Next

**The A2A boundary demo.** This is the session that makes everything
demonstrable as a complete system.

A lightweight Groq-powered network caller that:
1. Takes a natural language question
2. Uses Groq (Llama-3.3-70B) to decide which ACP Track N tool to call
3. Calls ACP via **real MCP protocol** (not in-process like the demos)
4. Gets the governed result back
5. Uses Groq to write a prose answer

**Demo flow:**
```
You type: "What is the path from the Mumbai branch to HQ core switch?"
         ↓
Groq reasons: "This needs find_path — source=branch-sw-01, dest=hq-core-sw-01"
         ↓  MCP protocol call with JWT token
ACP: checks token ✅ checks policy ✅ runs BFS → returns path
         ↓
Groq writes: "Traffic from Mumbai branch traverses 3 hops:
              Branch-SW-01 → Branch-cEdge-01 → HQ-cEdge-01 → HQ-Core-SW-01,
              crossing the SD-WAN OMP tunnel between the two edge routers."
         ↓
Audit log records the governed tool call.
```

That is the portfolio demo. Natural language in, governed answer out,
audit trail proves governance happened.

---

## 9. Session Continuity

**Start Block 5 with:**
```
cd D:\project-acp
.venv\Scripts\activate
```
Tell the next session:
> "ACP is at commit 807aaa9. Track C (Block 1) and Track N (Blocks 2-4)
> complete. LD-12 satisfied. Next is Block 5 — A2A boundary.
> Build a lightweight Groq-powered network caller that calls ACP Track N
> tools via real MCP protocol and returns prose answers to natural
> language questions. Upload this document + ACP_ARCHITECTURE_AND_TRUE_STATE_1.md
> to start cleanly."

---

*AbhavTech Consulting | Rajmohan Mangattu | CCIE Collaboration #55207*
*Document written from working lab — not ahead of it.*
*31 July 2026 | Session 2 debrief*
