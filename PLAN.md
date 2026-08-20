# Thropif.ai — 7 Phase Build Plan

> The app IS an OOi object. We build it the way we build everything: L1 → L7.
> Each phase answers one 00i question about the app itself.

---

## Phase 1 — GIVER (L1): What does this app give?

> *"You give first, before you ask."*

**Build the thing that gives value on day one. No signup. No tokens. Just useful.**

| Build | What | Tech |
|---|---|---|
| `app/main.py` | FastAPI at :7700 | FastAPI + uvicorn |
| `app/static/index.html` | HTMX dashboard shell — 8 app tabs | HTMX + Alpine.js |
| `store/thropif.db` | Single SQLite file: objects + cells + edges + embeddings + ledger | sqlite-vec |
| `harness/scaffold.py` | `thropif new person "Hakkı Dut"` → creates full folder structure | Python stdlib |
| Templates | person, product.cosmetic.dermaceutical, brand, company, supplier | YAML |
| First objects | Scaffold all 19 BP Derma SKUs + 12 people + 6 brands | scaffold.py |

**Acceptance:** `python3 app/main.py` opens browser, you see 37 objects on the dashboard, each with an empty hourglass. The app GIVES something — a structured view of your business — before it asks anything.

---

## Phase 2 — FAIR (L2): Is the data structure fair?

> *"Is it fair? You deal squarely."*

**Make sure every object type gets the same treatment. Same 3,199 cells. Same hourglass. Same truth.rate. No object is a second-class citizen.**

| Build | What | Tech |
|---|---|---|
| Template inheritance | `Thing > Product > Physical > Cosmetic > Dermacosmetic > Dermaceutical` | YAML chain + resolver |
| 7×7 matrices | One 00i-matrix.yaml per object type (person done, product next, brand, company, supplier, project, agent) | YAML |
| Object browser | App #5 OBJECTS — browse all objects, see L1-L7, filter by type/truth | HTMX partial |
| Interconnections | When you scaffold a product, auto-link to its brand + supplier + formulator | edges table in SQLite |
| L0 ledger | SHA-256 hash chain — every scaffold, every edit, every link recorded | SQLite table |

**Acceptance:** Every object type has a complete 7×7 matrix. Navigate product.1032 → see brand.bp-derma → see person.hakki-dut → see company.pelin-kozmetik. The graph exists.

---

## Phase 3 — TRUTHFUL (L3): Is the data real?

> *"Is it true? You say what's real."*

**Fill the objects with real data. Not AI-generated — scanned from actual files on disk. The truth comes from evidence, not invention.**

| Build | What | Tech |
|---|---|---|
| RAG thunderlightning | Scan estate → count keywords/tags per object → auto-fill cells with evidence + source citation | search.py + memory.py |
| OCR intake | Drop a PDF in `_inbox/` → OCR → classify → store in correct layer | tools/ocr.py + classify.py |
| 12-scanner collector | Wire into app: registry, vault, datacenter, projects, sessions, restart, agents.md, dev-status, OCR inbox, memory, CRM, OOi cross-ref | collector.py (done) |
| Evidence view | Each cell shows: score, evidence text, source path, timestamp | HTMX partial |
| Search (App #4) | Unified search — vault/projects/CRM/OOi/memory — returns OOi-typed results | search.py |
| Memory (App #6) | Ingest → embed → recall. Browse embeddings. Ingest control. | memory.py + sqlite-vec |

**Acceptance:** Run `thropif scan "Amino Acid Gel"` → 50+ findings from real estate files → cells fill with cited evidence → truth.rate moves from 0% to 20-40%.

---

## Phase 4 — LOYAL (L4): Does it prefer the network?

> *"Does it prefer the network? You stay."*

**The evidence core. The equator. Maximum data density. This is where the 7 agents evaluate, the models run, the benchmark compares. The app becomes self-sustaining.**

| Build | What | Tech |
|---|---|---|
| 7 AI agents | Scout→Auditor→Verifier→Watcher→Council→Listener→Elder | evaluator/evaluate.py (done) |
| Model router | Load balancer: max 2 local, cloud spillover, cost tracking | config/router.yaml + engine |
| Model setup (Settings) | Assign model per layer, test connections, see cost | HTMX settings panel |
| Dashboard (App #1) | Enterprise bridge — 7 agent stations, live WebSocket progress | WebSocket + HTMX |
| Evaluate (App #3) | Input name → watch 7 agents → see hourglass fill in real-time | WebSocket live view |
| Benchmark (App #7) | Run same object through 3 model configs, compare truth.rate + cost | evaluate.py --benchmark |
| MCP endpoints | Expose all tools as MCP: `thropif mcp serve` | FastMCP v3 |

**Acceptance:** `thropif evaluate "Mark Meier"` → 7 agents run in parallel → dashboard shows live progress → truth.rate reaches 57%+ → benchmark shows which model config is cheapest.

---

## Phase 5 — RESPECT (L5): Is the expertise earned?

> *"Is respect earned? By contributing, not claiming."*

**Expert network. People evaluate each other. Peer consensus. The masks and perspectives make the same data look different to different viewers.**

| Build | What | Tech |
|---|---|---|
| Masks | Agent/supplier/client/project masks — layer-based access control per viewer | mask config in YAML + filter in API |
| Perspectives | Same object, 4 views: perspective (full), skill (L3+L4), client (L1+L4+L6), user (L1+L6) | HTMX view switcher |
| Expert callout | Symbion8 integration: call out experts → they evaluate → results flow back | appflow + webhook |
| Peer evaluation | Person A evaluates Person B on L5 factors → consensus weight accumulates | peer_eval table in SQLite |
| Contribution tracking | Measure: who gives how much, how often, how good | contribution score in cells |
| App monitor (Settings) | Monthly cost, member coverage, model costs | cost-ledger.jsonl → dashboard |

**Acceptance:** Dr. Osama's mask shows him L1-L6 of a product but L7 is locked. A supplier sees only L1-L2. Anaïs's contribution score is computed from her actual inputs.

---

## Phase 6 — LISTENING (L6): Does it respond?

> *"You hear before you speak."*

**The pipeline system. The harness. The node editor. The app listens to data and responds with processing. Workflows execute. AppFlows connect systems.**

| Build | What | Tech |
|---|---|---|
| Node editor (App #2) | litegraph.js — OOi custom nodes, dark theme, JSON save/load | litegraph.js + Canvas2D |
| Pipeline engine | Execute node graphs: topological sort, per-node caching, typed sockets | harness/engine.py |
| Workflow YAML | Define intake/evaluation/sync workflows as YAML | harness/workflows/ |
| AppFlows | Symbion8 → Thropif.ai → jDax → OOi Store automation | harness/appflows/ |
| Triggers | Watch folders, cron schedules, webhooks, manual | harness/watch.py |
| OCR app (App #8) | Visual intake: drag file → OCR → classify → store → see result | HTMX upload + WebSocket |
| Tool add-ons | Manifest per tool, unlock logic, usage tracking | tools/*/manifest.yaml |

**Acceptance:** Design a workflow visually in the node editor → save as JSON → engine executes it → data flows through nodes → objects update → truth.rate changes. Drop a PDF in inbox → automated pipeline processes it end-to-end.

---

## Phase 7 — TEACHING (L7): Does it make others better?

> *"You pass it on. The person who teaches gets everything."*

**The gold seal. The synthesis. Token economics. Marketplace. The app teaches others how to build their own OOi systems.**

| Build | What | Tech |
|---|---|---|
| Token tier system | Free (3 bots) / Token (buy add-ons) / Contributor (earn full 7) | token/tiers.yaml + access.py |
| Template marketplace | Share/sell OOi templates — cosmetics, pharma, tech, any domain | templates as packages |
| Multi-user auth | MemberID via auth.meierdynamics.de → Person OOi → tier | SSO integration |
| BuyPool | Experts buy into marketing pools with contribution credits | buypool integration |
| Multi-country testing | Track marketing results per territory | market_test table |
| GraphRAG | Traverse interconnections graph: "find all products whose L5 expert is Dr. Osama" | SQLite recursive CTE → LadybugDB |
| Deployment | thropif.ai domain live, Symbion8 connected, 3 bots bridging | nordstar VPS |

**Acceptance:** A new user signs up → gets 3 bots free → uses the app → contributes knowledge → truth.rate rises → tools unlock → reaches L7 (Teaching) → gets full access → gold seal. The cycle completes.

---

## The Circle

```
Phase 1 GIVER      → the app exists and gives value
Phase 2 FAIR       → the data structure treats everything equally
Phase 3 TRUTHFUL   → the data is real, scanned from evidence
Phase 4 LOYAL      → the 7 agents evaluate, models run, network forms
Phase 5 RESPECT    → experts contribute, peers measure, masks filter
Phase 6 LISTENING  → pipelines respond, workflows execute, systems connect
Phase 7 TEACHING   → the app teaches others, tokens flow, the network grows

00i asks → OOi answers → truth.rate measures → L0 records → the cycle repeats.
```

Each phase makes the previous one deeper. Phase 1 without Phase 3 is empty structure. Phase 4 without Phase 2 has nothing to evaluate. Phase 7 without Phase 1 has nothing to teach.

**The app IS the OOi object. Building it IS filling the hourglass.**
