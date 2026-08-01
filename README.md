
---

## Demo — the A2A boundary in action

A natural-language question about a Cisco SD-WAN network, answered end to end
through the governed MCP boundary.

### 1. ACP server running

The governed MCP server starts and serves both `/health` and `/mcp` on port 8100.

![ACP server starting](docs/images/1-server-start.jpg)

### 2. The A2A flow — natural language to governed tool call

The caller grounds the LLM with real inventory, Groq picks `find_path` with the
correct parameters, the code validates them against the real topology, then calls
ACP over the real MCP protocol.

![A2A flow](docs/images/2-a2a-flow.jpg)

### 3. The governed answer

Groq composes a prose answer from the governed result — 2 hops across the SD-WAN
OMP tunnel, every fact traced to the topology.

![Governed answer](docs/images/3-answer.jpg)

### 4. Governance blocks an unauthorized caller

The same question with a `viewers` token. Governance blocks the flow at the first
tool call — no inventory returned, no answer, distinct audit reason.

![Governance block](docs/images/4-governance-block.jpg)

---
