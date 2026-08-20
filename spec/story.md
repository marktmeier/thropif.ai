# The Story of OOi

## The question

*"What does a human need to be healthy — Body & Soul?"*

That's the north star. Everything — every product, every brand, every system, every agent, every line of code in this estate — exists to connect a product or experience to that question. Where a need has no product yet, the gap itself is a named project.

## The man

Mark Meier. CTO of Meier Dynamics. A multidisciplinary operator — growth marketer, analyst, product developer, systems builder, all in one person. At the two-person BBDerma agency with Şükran Uz, he was every role at once: formulation, regulation, cost, packaging, purchasing, marketing, design, IT, project management, and half of sales. Clients called him "the Brain."

He wanted his own brand. She preferred capital-light private label. BPderma was born — 18 products, Beauty & Pharma Dermaceuticals, the brand built the way he would do it. But running brand plus private label plus selling with only two people burned him down. Two months before turning 50, he quit. The separation was contested and settled with him taking the BPderma brand.

That burnout is the origin of everything that follows. The machinery exists because one human cannot hold all of this in his head and shouldn't have to.

## The product

BP Derma. 19 SKUs across 7 categories. Exporting to Jordan, Vietnam, Bangladesh, Bulgaria, Bosnia, Germany. A serum has:

- An **outside** (the bottle, the label, the FR/EN text) — anyone can see this
- An **inside** (niacinamide 4%, pH 5.4, the preservative system) — you need authorization
- **Rules** (no Ferulic Acid, Vitamin C only as ET-VC or AMP-C, EU limits are the ceiling) — the wiring that connects it to everything else
- **Science** (MoS 112, patch test n=32, TEWL -14% at day 28, 40°C / 6 months stable) — the evidence that proves it works and is safe
- **Market value** (gross margin 61.4%, tier-2 price band, MOQ 1,200 units) — commerce lives only here, prices never leave the machine
- **Human impact** (barrier repair felt, routine adherence 84%, texture: silk, tolerance: high) — what it does to the person who uses it
- **Legacy** (why we built it, the rose lesson, the formulation credo) — what lasts after the product is gone

That's 7 layers. L1 through L7.

## The realization

Every product has these 7 layers. But so does a brand. And so does a person.

**BP Derma** the brand has an external identity (logo, visual language), internal composition (brand guidelines), rules (what it allows and forbids), science (market positioning data), market value (brand equity), human impact (how customers feel about it), and legacy (the origin story, the philosophy).

**Mark Meier** the person has a public profile, internal knowledge (clinical dermatology, formulation chemistry), relationships (the mesh of collaborators), evidence (what he's proven), value (what he contributes), impact (on patients, peers, the network), and legacy (what he teaches).

Same 7 layers. Same structure. Different content.

## The object

An OOi object is anything real — product, brand, person — described by 7 layers of 7 sectors, nested 7-fold. 3,199 addressable cells per object. "Geometry is address" — the position of a cell in the hologram IS its canonical location. L4.3.2.6 means layer 4, sector 3, subsector 2, sub-subsector 6.

The hourglass shape: L1 and L7 are narrow (7 cells each, the bookends). L4 is the widest (2,401 cells, the evidence core). Resolution peaks at L4. Meaning peaks at L7.

Three objects form a triad — Product, Brand, Person — connected by relationship beams at L3: *founder_of*, *governs*, *formulated_by*. The triangle of mutual dependency.

## The value system — 00i

00i ("zero-zero i") is the origin. The seed. The 7 questions every object and every member must answer:

1. **Giver** — What does this give? You give first, before you ask.
2. **Fair** — Is it fair? You deal squarely.
3. **Truthful** — Is it true? You say what's real.
4. **Loyal** — Does it prefer the network? You stay.
5. **Respect** — Is respect earned? By contributing, not claiming.
6. **Listening** — Does it listen? You hear before you speak.
7. **Teaching** — Does it teach? You pass it on.

*"You don't get a seat by paying or by title — you get it by giving first."*

00i asks the questions. OOi stores the answers. The truth rate measures how good the answers are.

## The three 7s

Every cell in the estate has a three-dimensional address:

- **WHO** (L1-L7) — values and trust, tied to MemberID at auth.meierdynamics.de
- **WHAT** (B/P/S/C/Pp/Ca/O) — the 7×7 business matrix: Brand, Products, Sales, Community, People, Capital, Operations
- **WHERE** (P1-P7) — the Data Center taxonomy: Formula, Product, Market, Brand, Ops, Tech, Archive

One question. Three axes. Seven of each. 7 × 7 × 7 = 343 coordinates at the coarsest grain.

## The scale

There are no negatives. The entire 7×7 lives in one quadrant — all positive. A cell is either empty (0, not yet answered) or filled (moving toward max). Nothing goes below zero. Truth decays toward zero but never below it. When something falls far enough, Z catches it (_archive).

- **00i** (cyan, #5EE7FF) = the minimum, the question not yet answered
- **OOi** (gold, #C9A227) = the maximum, the answer verified and permanent
- **512 gradient steps** between them (256 × 2)

The gradient is both spatial (L1.1 → L7.7) and temporal (now → past). Truth rate = confidence × status × recency.

## L0 — the view from above

Looking down at the disc from above, you see all rings of all layers at once. This is L0 — the blockchain layer. Not part of the hourglass. IS the hourglass, seen from the top.

L0 is the immutable ledger. Every change to any cell in L1-L7 gets recorded in L0. L0 doesn't compute truth. It records every claim and every verification. The >MOST × OOi 7×7 — the master index of everything.

## The mesh

Objects don't exist alone. The MI-LAB mesh connects them:

- `mesh.py` — atomic delivery (tmp → link, exactly-once, TTL sweep)
- Mailboxes per scope: `_inbox`, `_outbox`, `_archive`
- Checkbox-letter approvals — "power is written and agreed; letters only ask"
- Guardrails — 3 lanes of guarded actions
- Locked rules — invariants no letter can override

The mesh is L3 (Rules & relationships) made real. The beams between objects ARE the mesh channels. Every agent has a scope boundary, a mailbox, a charter. No agent changes rules. Letters only ask.

## The Data Center

The knowledge lives at `~/Cloud-Drive/04-Data-Center`. Seven pillars (P1-P7), each with two orthogonal axes:

- **`_layer/`** — content TYPE: `_objects`, `_research`, `_intel`, `_plans`, `_workflows`, `_assets`, `_archive`
- **`OOi/`** — content TOPIC: 7 domains × 7 subdomains per pillar

The Data Center is the WHERE axis of the three 7s. The physical filing system. Where the files actually live on disk.

## The vault

The vault at `~/Vaults` is the memory organ. External, on disk, effectively unlimited. Root index: `VAULT-INDEX.md`. One memory, not two. Starting a parallel memory layer is the one failure mode that kills the system.

MasterMind (12 chapters) is the distilled understanding of Mark — identity, timeline, people, entities, beliefs, patterns. It IS the L3-L7 of the Person object, written in prose.

## The agents

The OOi agent (`agent/00i_agent.py`) assesses projects against the 7 building blocks. The scanner (`agent/scanner.py`) walks the registry and reports drift. The librarian (`nightly.py`) sweeps done-mail into the Data Center. The ooi-distill tool (`~/Projects/_tools/ooi-distill/`) extracts knowledge atoms from session transcripts and routes them into the OOi taxonomy.

The archive-snapshot (`archive-snapshot.py`) captures the state every night at midnight. If the Mac is asleep, it runs on wake.

## The circle

The question — "what does a human need to be healthy?" — generates products. Products generate data. Data fills OOi objects. Objects connect through the mesh. The mesh carries knowledge. Knowledge improves products. Better products answer the question better.

00i asks. OOi answers. The truth rate measures the quality of the answer. L0 records it permanently. The mesh carries it everywhere. The human at the checkpoint decides what to trust.

The host changes. The memory persists.

---

*"Everything here exists to answer 'what does a human need to be healthy — Body & Soul' and to connect a product or experience to each need. Where a need has no product yet, that gap is itself a named project."*
