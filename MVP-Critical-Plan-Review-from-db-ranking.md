# Critical Plan Review — International Student & Parent Advisory Platform

_Reviewed as Senior Technical PM / Full-Stack Architect. Date: 2026-07-06._

**Confirmed constraints driving this review:**
- Primary audience: **Mainland Chinese families**
- Model: **Freemium B2C subscription**
- Data readiness: **~none yet** (data acquisition is the critical path)
- Team: **2–4 people**
- Timeline: **4-week MVP**
- Stack: Next.js 14 (App Router) · Supabase (Postgres + pgvector + Auth + Edge Functions) · Mapbox GL JS · Tailwind · Claude Code / Vibe Coding

---

## Three assumptions rejected up front

1. **"Top 150 universities" is vanity scope.** With zero existing data, 150 × ~25 deep fields = 3,000+ hand-verified data points, many (safety, Chinese-student ratio, 归国就业 outcomes, visa policy) not in any single clean source. A team of 2–4 cannot verify that AND build map AND build agentic RAG in 4 weeks. **Cut to 40 universities.** Depth is the moat; breadth loses to Niche.

2. **"Zero hallucination" is a claim that will burn you.** Not achievable, not honest. One screenshotted wrong tuition number in a 家长群 destroys trust permanently. Reframe as **grounded + cited + abstaining**: answer only from verified data, cite the source row, say "no verified data" rather than guess. Shippable and defensible.

3. **The AI advisor is NOT the moat, and Niche/College Board are NOT the competitors.** Anyone can wrap Claude + pgvector. Real competitors: **留学中介 (新东方前途, 启德, 立思辰)** and **小红书/知乎 study-abroad KOLs**. Moat vs. them = a **verified, China-lens structured dataset** + a **crowdsourced correction loop**. The AI is delivery, not moat.

---

## 1. Strategic Differentiation Gaps

**Missing China-specific data points.**
- Problem: Listed fields are generic. Decision-driving fields for Chinese families are absent/underspecified: 归国就业 recognition (教育部 recognized list / employer awareness), safety framed for parents (incidents involving intl students, neighborhood-level — not a US crime index), visa/post-study runway (UK Graduate Route, US OPT/STEM, HK IANG — and these change), all-in RMB cost incl. FX, Chinese community density (CSSA, groceries, direct flights).
- Solution: Define a first-class **"China-Lens Field Set"** in the schema. These fields ARE the product.
- Effort: Med · Impact: High.

**Serving parents without diluting students.**
- Problem: Parents optimize safety/cost/prestige-legibility; students optimize fit/program/lifestyle. One UI for both serves neither.
- Solution: Single dataset, **两个视角 toggle (学生视角 / 家长视角)** that re-weights map filters and reorders the school card. Same data, different default sort + highlighted fields.
- Effort: Low · Impact: High.

**Defensible MVP moat.**
- Problem: Map (commodity) and AI (commodity) are not moats.
- Solution: (a) verified China-lens dataset + (b) crowdsourced correction loop ("发现数据有误?" on every field → ETL queue). Compounds with users; agencies can't crowdsource, KOLs can't structure.
- Effort: Med · Impact: High.

---

## 2. Data Architecture & RAG Reliability

**Flat data model fights hybrid search.**
- Problem: One wide 25-column table can't cleanly serve structured filters (map) and semantic retrieval (advisor).
- Solution: Three tables:
  - `universities` — stable structured facts; B-tree indexes on filterable numerics, GIN for array fields (e.g. programs).
  - `university_facts` — typed key-value: `fact_type, value, source_url, verified_at, confidence`. Enables per-fact citation + abstention.
  - `fact_chunks` — NL rendering of each fact + `embedding vector`, `source_fact_id`. RAG retrieves these; every chunk points back to a verifiable fact.
- Effort: Med · Impact: High.

**You may not need pgvector for MVP.**
- Problem: 40 universities is a tiny corpus; semantic search over ~40 docs often loses to structured SQL + keyword, and adds hallucination surface.
- Solution: **Structured-filter-first retrieval** — profile → SQL filters on `universities`; use pgvector only for fuzzy qualitative layer (campus vibe, essay themes). Facts come from rows, not embeddings.
- Effort: Low · Impact: High.

**Evaluation framework (build week 2, run continuously).**
- Problem: "Zero hallucination" with no measurement is a slogan.
- Solution:
  - **Golden set:** 50 hand-written Q&A pairs + known-correct answer + exact source row (stored as table; re-run on every prompt/data change).
  - **Citation accuracy:** every factual claim carries `source_fact_id`; auto-check the cited fact contains the claimed value. Target ≥ 98%.
  - **Hallucination rate:** LLM-as-judge flags untraceable claims + human spot-check 20/week. Target < 2%.
  - **Abstention correctness:** 10 no-data questions must be declined, not invented. Target 100%.
  - **Relevance:** thumbs up/down + "would you show this to your parents?"
- Effort: Med · Impact: High. **This is the launch gate.**

**ETL freshness safeguards.**
- Problem: Visa/cost data goes stale; wrong visa answer is trust-destroying.
- Solution: `verified_at + source_url + confidence` on every fact. Surface **"数据核实于 [date]"** on volatile fields. Edge Function + cron flags facts past freshness SLA (visa 30d, cost 90d, rankings 365d) to a review queue. Human-verify policy; automate only FX conversion.
- Effort: Med · Impact: High.

---

## 3. UX & Map Interaction Refinements

**Filtering alone doesn't accelerate family decisions.**
- Solution — three high-impact interactions:
  - **Compare tray:** add up to 4 pins → side-by-side table (agencies do this in Excel; do it live).
  - **Affordability overlay:** enter RMB budget → map recolors green/yellow/red by all-in cost. Answers the parent's first question in one gesture.
  - **"像这样的学校":** click a school → highlight similar on cost/safety/program. This is where pgvector earns its place.
- Effort: Med · Impact: High.

**Unify AI output with map/DB (no siloed chat).**
- Solution: Advisor outputs are **objects, not chat bubbles.** Each match-matrix row = a live map pin + sidebar card; clicking a recommendation flies the map to it. The deliverable IS a filtered, AI-authored view of the database. Chat = input; map + cards = output surface.
- Effort: Med · Impact: High. Makes it AI-native, not "ChatGPT in a sidebar."

---

## 4. MVP Scope & Risk Mitigation

### Ruthless cut list
| Feature | Verdict | Why |
|---|---|---|
| 150 universities | **CUT → 40** | Data sourcing is the critical path; 40 deep > 150 shallow. |
| "Zero hallucination" claim | **CUT** | Replace with cited + abstaining. |
| Financial plan generator | **CUT** | Highest-liability output; post-MVP. |
| Essay brainstorming | **CUT from launch, locked teaser** | Not DB-grounded → highest hallucination risk. Drives paywall. |
| Personalized timeline | **KEEP (templated logic, not LLM)** | High value, deterministic, low risk. |
| School-match matrix | **KEEP** | Core AI deliverable; ground it hard. |
| Map + compare + affordability | **KEEP** | Core value, works with zero AI. |
| Crowdsourced corrections | **KEEP (lightweight)** | Cheap, and it's the moat. |

**MVP in one sentence:** an interactive map + comparison tool over 40 deeply-verified China-lens university profiles, with an AI that produces a cited, map-integrated school-match matrix from a profile — and honestly abstains when it lacks data.

### Top 3 risks + mitigations
1. **Data sourcing blows the timeline (highest probability).** → One member owns only data from day 1; cut to 40; strict P0/P1 field tiers; "未核实" placeholders for P1 rather than blocking; Claude Code scrapers for structured public fields, humans for China-lens fields.
2. **A single wrong high-stakes fact destroys community trust.** → `verified_at` + source link on volatile fields; abstain on unverified; financial planner cut; public correction loop ("48 小时内核实更正").
3. **Freemium tier mis-designed (no growth, or gives away moat).** → Free = full map + comparison + all 40 profiles (top-of-funnel, out-guns alternatives). Paid = AI deliverables. Prove free-tier DAU + paywall conversion before buying breadth.

### MVP beta success metrics
- **Activation** (signup → ≥1 AI deliverable): > 40%
- **AI query completion** (session → rendered deliverable): > 70%
- **Grounding integrity:** citation ≥ 98%, hallucination < 2% — **hard launch gate**
- **Trust signal:** data-correction submissions / 100 users (want non-zero; P0 errors trigger review)
- **Retention** (D7 of activated users): > 25%
- **Monetization intent** (paywall → upgrade click): > 15%

---

## Prioritized action list — next 7 days
1. Lock scope to 40 universities; finalize P0/P1 field list incl. China-Lens Field Set. _(Whole team, day 1.)_
2. Design + migrate 3-table schema in Supabase. _(1 dev, days 1–2.)_
3. Source first 10 universities end-to-end to reveal real per-school cost. _(Data owner, days 1–5.)_
4. Build 50-pair golden eval set. _(1 person, days 2–4.)_
5. Map with real pins for 10 schools + hover preview + compare tray. _(1 dev, days 3–6.)_
6. Prototype structured-filter-first advisor (profile → SQL filters → cited matrix); run golden set. _(1 dev, days 4–7.)_
7. **Day 7 checkpoint:** real per-school data cost × 40 vs. calendar. If it doesn't fit, cut universities — not quality.
