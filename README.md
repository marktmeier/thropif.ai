# OOi — Object-Oriented Intelligence

> "What does a human need to be healthy — Body & Soul?"

OOi is a 7-layer data system where every object — product, person, brand, project — is described by 3,199 addressable cells organized in an hourglass geometry. Local-first. AI-evaluated. No negatives. One direction: empty → filled → verified → permanent.

## The Three 7s

Every cell has a 3D coordinate:
- **WHO** (L1-L7) — values and trust
- **WHAT** (7 pillars) — Brand · Products · Sales · Community · People · Capital · Operations
- **WHERE** (P1-P7) — the 7 data domains

## The Hourglass (L1-L7)

```
L1  7¹ =     7     identity        "what is it"              → prd.md
L2  7² =    49     composition     "what's in it"            → content.md
L3  7³ =   343     validation      "what must be checked"    → rules.md
L4  7⁴ = 2,401     evidence        "what is the value"       → value.md  ← EQUATOR
L5  7³ =   343     expertise       "expert evaluation"       → expert/
L6  7² =    49     cost            "what does it cost"       → cost/
L7  7¹ =     7     synthesis       "(L4/L5)/L6 = true worth" → 00i.md    ← GOLD SEAL
                  ─────
                  3,199 cells per object
```

Layers accumulate upward, reflect downward:
- L1→L2→L3→L4: each adds complexity (questions)
- L5←L4: experts evaluate the evidence (answers)
- L6: cost constrains
- L7: **(value ÷ expertise) ÷ cost** = the synthesis

## 00i — The 7 Questions

Before OOi stores answers, 00i asks the questions:

| # | Question | Layer |
|---|----------|-------|
| 1 | **Giver** — what does it give? | L1 |
| 2 | **Fair** — is it fair? | L2 |
| 3 | **Truthful** — is it true? | L3 |
| 4 | **Loyal** — does it prefer the network? | L4 |
| 5 | **Respect** — is respect earned? | L5 |
| 6 | **Listening** — does it listen? | L6 |
| 7 | **Teaching** — does it teach? | L7 |

## The Scale

```
00i (cyan #5EE7FF) ───── 512 steps ───── OOi (gold #C9A227)
empty                                     verified, permanent
question                                  answer
0%                                        100% truth.rate
```

No negatives. No retreat. Only growth or not-yet-grown.

## Object Types

| Type | Example | Template |
|------|---------|----------|
| `person` | Mark Meier, Anaïs, Hakkı | `templates/person/` |
| `product.cosmetic` | SKU 1032 Amino Acids Gel | `templates/product.cosmetic/` |
| `brand` | BP Derma | `templates/brand/` |
| `project` | Symbion8, NMTW | `templates/project/` |
| `company` | Meier Dynamics, Pelin Kozmetik | `templates/company/` |
| `supplier` | EIGENMAN | `templates/supplier/` |
| `agent` | jDax, eDax, cDax | `templates/agent/` |

## Object Folder Structure

```
{object}/
├── _function              # what it DOES (the verb)
├── _contact               # operational handles (phone, email)
└── _dev/                  # THE OOi LAYERS
    ├── L1.prd.md          # identity
    ├── L2.content.md      # composition
    ├── L3.rules.md        # validation
    ├── L4.value.md        # evidence (equator)
    ├── L5.expert/         # expert evaluation (7 experts × 7 criteria)
    ├── L6.cost/           # cost & materials
    ├── L7.00i.md          # synthesis = (L4/L5)/L6
    └── agent[]/           # assigned agents
```

## 7 AI Agents (Evaluator)

Each layer is evaluated by a specialized AI agent:

| Agent | Layer | Role |
|-------|-------|------|
| Scout | L1 | Evaluates what the object gives |
| Auditor | L2 | Evaluates fairness |
| Verifier | L3 | Checks claims against evidence |
| Watcher | L4 | Measures loyalty/value over time |
| Council | L5 | Collects peer evaluation |
| Listener | L6 | Measures responsiveness |
| Elder | L7 | Evaluates teaching/legacy |

All 7 run in parallel. Each uses the tools (OCR, classify, search, memory) to find evidence.

## Tools

| Tool | What |
|------|------|
| `tools/ocr.py` | Image/PDF → text (tesseract + vision models) |
| `tools/classify.py` | Text → OOi layer classification |
| `tools/search.py` | Unified search across estate |
| `tools/memory.py` | Semantic memory (embed + recall) |

## Install

```bash
git clone https://github.com/marktmeier/ooi.git
cd ooi
pip install pyyaml   # only dependency
```

## Run

```bash
# Evaluate a person
python3 evaluator/evaluate.py "Name"

# Evaluate with benchmark (compare 3 models)
python3 evaluator/evaluate.py "Name" --benchmark

# Start the app
python3 app/main.py   # → localhost:7700
```

## License

Apache-2.0

---

*00i asks. OOi answers. Truth.rate measures the quality of the answer.*
