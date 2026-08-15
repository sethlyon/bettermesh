# BetterMesh by BetterRX — Closed-Network Dispatch for Hospice DME

BetterRX Builder Day Bounty · DME Ordering and Visibility Challenge

> Planning document for the BetterRX bounty submission, published alongside the
> prototype in this repo.

**Name rationale (talking point, not a slide):** *Mesh* names the shape of the
dispatch model — a closed mesh of the hospice's own contracted vendors, not one
brittle point-to-point vendor relationship. When one link in the mesh is about to
fail, the order re-routes to another node already in that same mesh instead of
stalling. "by BetterRX" keeps the parent brand as the endorsing house and frames
this as a new product line, not a rebrand.

---

## The one-liner

When a hospice's DME order is going to miss a discharge window, the primary vendor
quietly fails and the hospice finds out too late. BetterMesh turns the hospice's
existing contracted vendor list into a live dispatch network: it detects at-risk
orders in real time, and automatically re-broadcasts them to the hospice's other
contracted vendors so the fastest one to confirm gets the job — before the
discharge slips.

**This isn't a hypothetical productization angle — it's BetterRX's existing
business model, extended one category.** BetterRX doesn't run hospices; it sells
software *to* hospices and operates a two-sided marketplace (a pharmacy network)
that fulfills on the other side. BetterMesh is the same shape for equipment: a
coordination and dispatch network between the hospice EMR and DME vendors, sold to
hospices as visibility-plus-reliability and to vendors as preferred-dispatch
access. It extends BetterRX's existing eRx footprint from medication into
equipment — same buyer, same discharge moment, same structure, not a new one.

---

## Why this problem

Two moments hospices don't control but always get blamed for:

1. **Discharge readiness.** A patient can't safely go home without a bed, oxygen,
   or a wheelchair in place. The vendor's timeline slips, and the hospice absorbs
   the CAHPS hit. Some hospices pad a full buffer day because they no longer trust
   the timeline. BetterRX's own team confirms this pattern directly: *"if a vendor
   fails to deliver on time, the hospice takes the reputational hit, not the
   vendor"* — most families never know which vendor was actually involved.
2. **Post-death pickup.** Retrieval is triggered by a phone call after a death.
   When it's slow, a grieving family stares at equipment they no longer need, and
   the hospice takes the blame for a vendor's delay — and keeps *paying* for it:
   BetterRX confirms the hospice is billed per equipment-day until pickup, with a
   stated target of pickup within 24 hours. That's not a vague cost, it's a
   number, and it's the number BetterMesh's dispatch now targets.

Both share one root cause: **there is no shared, reliable signal of delivery
status between the hospice and the vendor.** BetterRX's own discovery flagged
*delivery visibility*, not DME ownership, as the higher-leverage problem. I agree —
and I go one step further: visibility alone tells you you're about to fail.
BetterMesh does something about it.

---

## The core idea, and how it evolved

**Starting instinct:** "Why isn't this an Uber-style app that broadcasts an order
to every vendor and dispatches the best one?"

**Why the naive version breaks:** DME reimbursement under the Medicare Hospice
Benefit runs through pre-negotiated contracts tied to a specific vendor's NPI and
billing credentials. You can't dispatch to an arbitrary vendor and expect the
claim to clear. Inventory isn't fungible either — being closest doesn't mean
having a bed in stock.

**The version that survives contact with reality:** *Closed-network dispatch.* The
"network" is the 3-5 vendors the hospice **already contracts with** in that market.
The brief confirms hospices deliberately keep 2+ vendors per market as a manual
fallback. BetterMesh automates the fallback they already rely on — no new billing
relationships, no compliance wall.

**One deliberate extension — order splitting at placement:** If the primary vendor
has 90% of an order but no bed, BetterMesh can split the bed line-item to a second
contracted vendor as its own clean order, both delivering to the patient's home.
Two vendors, two clean claims, one patient — **no inter-vendor physical handoff**,
which is what would otherwise create a chain-of-custody and billing-fraud problem.
I show this as a capability, not the core demo, because it's where the
compliance story needs a real BetterRX conversation.

**The upgrade that makes risk trivial — shared inventory (two-tier):** Risk today
is *inferred* from ETAs. If vendors expose live inventory, risk becomes a *known
fact at order time* and dispatch becomes deterministic. But live inventory is
competitively sensitive and most vendors won't share it on day one, so
BetterMesh runs a two-tier model that works either way:

- **Tier 1 — integrated vendors (inventory shared).** BetterMesh knows exactly
  who has every line-item in stock. Dispatch is a rules problem: prefer a single
  contracted vendor who can fulfill the *complete* order, closest and soonest; only
  if no single vendor is complete does it expose the missing line-items to the rest
  of the network. No prediction needed — no AI needed here, and I say so. (Cost
  isn't wired into that ranking in the current code — see the roadmap below. Once
  vendor integrations and inventory disclosure are live, cost becomes a *secondary*
  signal: a tiebreaker among the vendors who can already fulfill the order in
  time, not the primary sort.)
- **Tier 2 — non-integrated vendors (no inventory feed).** BetterMesh falls back
  to the ETA-vs-window risk model and confirmation-broadcast. This is where a
  predictive risk score earns its place, flagging likely misses before an ETA even
  exists.

The two tiers also define the product's adoption gradient: it works on day one with
zero vendor integration (Tier 2), and gets sharper as vendors opt in (Tier 1).
"Integrate your inventory, get preferred dispatch" is a real incentive flywheel —
the vendors who share data win more volume, which pulls the rest of the network in.

**Validated after the fact, not designed to it:** BetterRX's own team names the
same three factors clinicians weigh when ordering — availability, price, speed —
and confirms hospices are typically locked into one primary vendor (maybe a
backup) with no real choice today; opening that up is explicitly what they want.
That's Tier 1/Tier 2 and the "best match" vendor ranking (confidence first, price
second — DME pricing is vendor-set, not insurance-set, so it has to be modeled
per-vendor) almost exactly. Worth saying in the room: I didn't reverse-engineer
this from the brief, it's independently the same shape they described unprompted.

---

## What I build (the vertical slice)

A single web app with two role-based views over one shared order timeline.

**It already works with zero integration.** Both roles reach BetterMesh the same
way today — a login. A hospice case manager can log in and create and dispatch an
order by hand, no EMR wiring required. A DME dispatcher can log in and see exactly
the orders and open network broadcasts relevant to their vendor, and accept them
the same way. The pre-discharge webhook and the deceased-status event (below) make
the hospice side faster and more automatic, but they're an upgrade to an
already-functional product, not a prerequisite for it — BetterRX could sell and
deploy this to a hospice and its vendors this week, on logins alone.

### Hospice case manager view
- **Pre-discharge equipment dispatch.** The patient's DME need already exists in
  BetterRX somewhere on the discharge record — a physician's order, a care plan
  line-item. One click on that existing record ("Dispatch equipment") sends the
  already-structured need (patient ID, HCPCS E-code, target discharge time)
  straight into BetterMesh. Nobody re-types an order; nobody has to know the
  patient's chart number by heart.
- See every active order with a live status and a **risk flag** when ETA threatens
  the discharge window.
- Mark a patient deceased → auto-generates a pickup order and notifies vendors. No
  phone call.
- *(Manual fallback: a plain structured form for the rare equipment need that
  isn't already on the discharge record — three dropdowns, no AI.)*

BetterRX names three hospice-side personas (admissions nurse, case manager,
director of nursing); the demo models the **case manager** persona specifically —
the other two are the same board with a different permission/approval scope, not
a different product, and I say so rather than pretend one login covers everyone.

### DME dispatcher view
- Inbound queue of orders and re-broadcasts, accept / confirm ETA.
- See only what's relevant to them (their orders + open network broadcasts).

### The dispatch engine (the differentiator)
1. Order arrives — via the pre-discharge dispatch integration (the default path)
   or the manual fallback form. BetterMesh checks whether any **Tier 1** contracted vendor has
   the *complete* order in stock → prefer single-vendor fulfillment, closest and
   soonest. If none is complete, expose only the missing line-items to the network.
2. If no inventory data (**Tier 2**), route to the primary contracted vendor and
   continuously evaluate risk: `ETA vs. discharge window`, vendor confirmation lag,
   equipment type, time of day.
3. When a Tier 2 order crosses the risk threshold, it's **re-broadcast to the
   hospice's other contracted vendors**. First to confirm within the window gets it.
4. Every state change is visible to both sides in real time.

---

## Where AI earns its place (and where it doesn't)

The brief demands I justify AI over a rules-based baseline. The honest answer for
this product is blunter than a table of AI/no-AI rows: **the primary application
doesn't need AI at all.** Routing an order to the right vendor in a known, closed
network — and re-routing it when one link is running late — is a rules problem,
not a prediction problem.

| Capability | Approach | Why |
|---|---|---|
| Order intake | **Integration, not AI.** The equipment need already exists as structured data in BetterRX (physician order / care plan line-item). I read it, I don't infer it. | There's no ambiguity for AI to resolve once the data's already structured at the source — that's the whole point of the pivot away from natural-language intake. |
| Dispatch, Tier 1 (inventory shared) | **Rules only.** No AI. | With live inventory, "who can fulfill the complete order, closest and soonest" is deterministic. |
| At-risk detection, Tier 2 (no inventory) | **Rules only** — `ETA vs. discharge window`. No AI. | A threshold catches the miss cleanly. Reaching for a model to do a comparison would be the "AI for AI's sake" failure mode, not a strength. |
| Pickup / dispatch routing | **Rules only.** No AI. | It's a confirmation broadcast, not a prediction. |

**Where AI genuinely earns its place is post-launch — not in the MVP — and it cuts
both directions, not just the vendor side.** Once real dispatch volume flows
through the network, BetterMesh can surface aggregate demand patterns back to
in-network vendors: which equipment types actually drive dispatch volume, so a
vendor can stock ahead of demand instead of reacting order-by-order. The same
model runs the other way for hospices: flag when a hospice's own contracted
vendor network is trending toward not being able to keep up with projected
demand, so the hospice gets advance warning to add or diversify vendor coverage
*before* it becomes a missed discharge, not after. Both are a real forecasting
problem, and the input data literally doesn't exist until the network has volume
— which is exactly why I don't fake a version of either for the demo. It's also
the two-sided value-add that makes "integrate with BetterMesh" a better deal than
staying manual: preferred dispatch and better stocking decisions for vendors,
earlier warning of network risk for hospices.

Cost envelope for the MVP: zero inference cost. Every dispatch decision is a rule
evaluated against data already on hand.

---

## The real complexity — and the launch plan that follows from it

The dispatch logic is simple on purpose — that's the point, not a limitation. The
actual implementation risk in this product is **integration and adoption**, not
algorithms:

- **Hospice-side integration.** Getting the pre-discharge equipment need and the
  deceased-status event to flow out of BetterRX (or the EMR) reliably and close to
  real-time.
- **DME vendor-side adoption.** Getting a hospice's 3-5 contracted vendors onto
  BetterMesh at all — accepting opportunities, and eventually sharing inventory
  for Tier 1.

Which is why a real launch is a **paired pilot**, not a rollout: one hospice's
BetterRX instance wired to send pre-discharge and deceased-status events, and that
hospice's actual contracted vendors onboarded to receive and confirm through
BetterMesh. Prove the mesh holds for one hospice's real network before
generalizing. It's also where the vendor-side AI forecasting story above becomes
real — it needs pilot volume to have anything to forecast from.

---

## Integration story (architecture-readiness = 15%)

**The core architectural bet: BetterRX already holds both triggers this product
needs, not just the buyer relationship.**

- **Pre-discharge equipment need (order trigger).** The DME need is already
  captured in BetterRX's discharge record — a physician's order or care plan
  line-item. BetterMesh doesn't create this data, it subscribes to it. For the
  demo: mock a webhook receiving an order payload shaped like the sample records
  (patient ID, HCPCS E-code, order type, target date). No live connection required.
- **Deceased status (pickup trigger).** A death is already a first-class event in
  BetterRX's medication workflow — active meds stop, controlled substances must be
  reconciled and disposed. BetterMesh subscribes to that same event to fire pickup
  instead of waiting on a phone call.
- Both triggers share the same two wiring options, and the same open question:
  - **BetterRX-native (fastest path).** Subscribe to the event BetterRX already
    has; no new EMR integration, no new data capture.
  - **EMR-sourced (system of record).** The event originates in the EMR (HCHB,
    Axxess, WellSky, MatrixCare) and flows via the same partner-connection layers.
    More robust, slightly more lift.
  - *Open question for Friday:* for both triggers, does the event land in BetterRX
    in near-real-time, or end-of-day / batch? Real-time makes the "instant dispatch"
    and "instant pickup" claims airtight; if either lags, trigger off the EMR
    instead. Same wire, different source.
- **Vendor inventory (Tier 1):** a simple inventory API/webhook per vendor (SKU →
  E-code → on-hand count). For the demo I seed two integrated vendors with stock
  and leave one as a Tier 2 fallback, so both paths show on screen.
- **EMR:** BetterRX's own team directly named **HomeCare HomeBase (HCHB)**,
  **MatrixCare**, and **WellSky** as the relevant home-hospice EMRs (kickoff Q&A) —
  lead with HCHB, which has a purpose-built DME integration layer for automated
  ordering + real-time patient status, and show the order/patient record shape
  crossing the boundary. Axxess follows the same partner-connection pattern but
  wasn't named by BetterRX directly — flag it as my own addition, not a confirmed
  one (there is no shared DME ordering standard regardless — HCPCS E-codes for
  identity, ANSI X12 837 for claims).

---

## Demo script (5 minutes)

1. **Integration-first order arrival.** Click "Dispatch equipment" on a patient's
   discharge record — a STAT CPAP need (E0601) that already exists in BetterRX for
   a 4:30 discharge. No form, no typing. The structured order lands in BetterMesh
   already assigned to the patient's non-integrated primary vendor.
2. **Discharge-readiness save (Tier 2).** That vendor's ETA lands at 5:10 → risk
   flag fires. BetterMesh re-broadcasts to two other contracted vendors; one
   confirms a 3:50 window. The discharge is saved on screen. *(This is sample order
   DME-10305, made real.)*
3. **Instant fulfillment (Tier 1).** Dispatch a hospital-bed need against
   integrated vendors. BetterMesh sees one vendor has the complete order in stock
   and dispatches instantly — no risk window to sweat, because inventory made it a
   known fact. Then dispatch a mixed order where no single vendor is complete and
   watch it prefer single-vendor first, then split only the missing line-item.
4. **Post-death pickup.** Mark a patient deceased. A pickup order auto-generates
   and hits the vendor queue instantly — the phone call that used to take hours,
   gone.

Covers the three scenarios the brief asks for — discharge readiness, post-death
pickup, service-failure prevention — plus the Tier 1 inventory ideal state. No step
here depends on AI; the honest AI story is the one two sections up (roadmap
forecasting), told rather than faked on screen.

---

## Why I beat today's market (differentiation = 30%)

Today: vendor-specific portal, phone, or fax; tracking (if any) trapped in the
vendor's own software; the fallback vendor is a manual phone tree. BetterMesh:
- Removes the re-entry step entirely — the equipment need never has to leave
  BetterRX and come back as someone's typed description of it.
- Surfaces delivery status to **both** sides in one pane.
- Converts the manual multi-vendor fallback into **automatic risk-triggered
  dispatch** within the existing contract set.
- Turns shared inventory into **preferred, deterministic single-vendor dispatch**
  for vendors who integrate — with a working Tier 2 fallback for those who don't.
- Replaces the post-death phone call with an EMR-triggered pickup.

It's not a prettier portal. It changes what happens when a delivery is about to
fail — which is the exact moment the hospice currently has no leverage.

---

## The productization case for BetterRX

Why this is a SaaS line BetterRX could own, not just a hackathon toy:

- **Adjacent to the existing wedge.** BetterRX already sits in the discharge moment
  via eRx for medication. Equipment is the same buyer (the hospice), the same
  moment (discharge and death), a natural second product.
- **BetterRX already holds both triggers, not just the buyer.** A death is already
  an event BetterRX must act on for medication discontinuation and
  controlled-substance reconciliation; a DME need is already captured in the
  discharge record as a physician's order or care plan line-item. BetterMesh
  reuses both signals — one currently used for meds, one currently just sitting in
  the chart — to drive dispatch and pickup with zero new data capture. The wedge
  isn't only that they have the customer; it's that they already have the *data
  signals* sitting unused for logistics.
- **Two-sided monetization.** Charge hospices for visibility + reliability
  (per-patient-day or per-seat SaaS); charge or upsell vendors for preferred
  dispatch and inventory integration — and, once the network has volume, for
  AI-driven demand forecasting that helps them stock ahead instead of reacting.
  Sell hospices the mirror image of that same forecast: early warning when their
  own contracted vendor network is trending toward a capacity shortfall.
  The network gets more valuable as both sides join — classic marketplace flywheel.
- **Zero integration lift to start.** The product is fully usable via login alone
  — hospices dispatch by hand, vendors accept by hand — before any EMR or
  inventory integration exists. BetterRX can sell and deploy against hospices and
  their vendors immediately; Tier 2 → Tier 1 integration work only sharpens what's
  already working, it doesn't unlock it.
- **Defensible data asset.** Every order, ETA, and outcome flowing through the
  network becomes proprietary reliability data — vendor scorecards, market-level
  benchmarks, and better risk models no single vendor or EMR can replicate.
- **Rides the EMR integration layers that already exist** (HomeCare HomeBase,
  MatrixCare, WellSky — named directly by BetterRX; Axxess is the same pattern but
  unconfirmed by them) rather than fighting them, so BetterRX is the connective
  tissue, not a rip-and-replace.

I present BetterMesh as a functional prototype of that SaaS product, not a
one-off — the demo is the thin slice, the pitch is the wedge.

---

## Honest risks / open questions for Friday

- **Does risk-triggered re-dispatch match reality?** Need a hospice operator to
  confirm what actually happens today when a primary vendor is going to be late.
  (I have direct access to a hospice owner to pressure-test this.)
- **Is there a DME vendor I can talk to?** The brief is hospice-heavy; the
  dispatcher-side workflow is my biggest assumption.
- **Contracting constraints on re-dispatch.** Are all contracted vendors equally
  billable for any order, or are there per-vendor equipment/coverage limits that
  constrain who a broadcast can go to?
- **Where does the equipment need actually live in BetterRX today?** Is it already
  a coded order (HCPCS-mappable) on the discharge record, or free text in a care
  plan? If it's free text, the mapping to an E-code needs to happen somewhere —
  ideally a deterministic lookup at the point the physician orders it, not an AI
  guess at dispatch time. Need a BetterRX product answer, not just a data-flow
  assumption.

---

## My edge

- Direct Supply background (senior-living medical equipment supply chain) — the
  vendor/logistics side of this exact category.
- A hospice owner next door to validate workflow and vouch for authenticity.
- Both sides of the gap BetterRX is trying to close, held by one builder — solo,
  not split across a team.

---

## Stack (buildable in a day)

- **Backend:** FastAPI + SQLite, seeded with the six synthetic sample orders.
- **Frontend:** lightweight — HTMX over React (server-rendered partials, no JS
  build/state layer); two role views via a simple toggle. BetterRX's own product
  is a responsive web app, not native (kickoff Q&A) — this isn't a shortcut, it's
  the right call independent of the deadline.
- **AI:** none in the MVP — intake is an integration read, not a parse; risk
  detection is a plain rule (`ETA vs. window`). The honest AI story lives on the
  roadmap (vendor demand forecasting), not in the stack.
- **Realtime:** simple polling for the shared timeline.
- Everything runs local on synthetic data. No PHI, nothing sent externally.

---

## MVP target for the hackathon

Real clock: Friday 2pm start → Saturday 2pm judging, ~one working day. Scope is
ruthless. **The MVP in one sentence:** a single web app, two role views, one shared
order timeline, demonstrating the *discharge-readiness save* and the *post-death
pickup* end to end on the brief's synthetic data.

### Must-have (this *is* the demo)
1. **Pre-discharge dispatch trigger** — a "Dispatch equipment" action on a mocked
   BetterRX discharge record sends a structured order (patient ID, HCPCS E-code,
   target window) straight into BetterMesh. This *is* the no-brainer integration
   story, not a nice-to-have.
2. **Shared order board** — orders with live status (Ordered → Dispatched → In
   Transit → Delivered), visible from both hospice and dispatcher views. The
   "single pane of glass" a hospice VP asks for in the brief.
3. **Risk detection (Tier 2, rules)** — flag an order red when `ETA > discharge
   window`. Must fire visibly on screen.
4. **Re-dispatch broadcast** — red order re-broadcasts to other contracted vendors;
   a second vendor confirms a better window; the flag clears. The differentiator.
5. **Post-death pickup trigger** — mark a patient deceased → pickup order
   auto-generates in the vendor queue. Cheap to build, high emotional resonance.
6. **Seed data** — the six sample orders, including DME-10305 (4:30 discharge /
   5:10 ETA) so the risk demo runs on *their* data.

### Should-have (add once the core is solid)
7. **Manual fallback form** — a plain structured form (no AI) for the rare
   equipment need not already on the discharge record.
8. **Tier 1 inventory path** — two vendors with a stock table; single-vendor-complete
   preference. Adds the ideal-state narrative.

### Won't-have (roadmap, say it out loud, don't build it)
- Order splitting / multi-vendor fulfillment (compliance story not demo-ready).
- Real EMR/eRx integration (mock the webhook shape + a diagram; brief allows this).
- AI-driven demand forecasting, both directions (vendor-side stocking, hospice-side
  network-capacity risk) — the real AI story, but it needs live network volume
  that doesn't exist until after launch.
- Cost-based tie-breaking among multiple capable vendors — not in the code today.
  Once vendor integrations and inventory disclosure are live, cost becomes a
  secondary ranking signal, used only to break ties among vendors who can already
  fulfill the order in time.
- Auth, real accounts, mobile (a Hospice/Dispatcher view toggle is enough).

### Build order (dependency-aware)
1. Data model + seed the 6 orders (SQLite).
2. Pre-discharge dispatch trigger (mocked webhook → order created).
3. Order board UI + role toggle.
4. Risk flag rule + visual state.
5. Re-dispatch action + second-vendor confirm.
6. Post-death pickup trigger.
7. **Checkpoint — winning demo exists.** Everything after is upside.
8. Manual fallback form.
9. Tier 1 inventory path.

Trap to avoid: over-investing in Tier 1 inventory because it's interesting. Judges
score *differentiation* + *core user problems* at 55% combined — both live in
items 1-6, not in the inventory model. A working scaffold lives in [`../app/`](../app/)
in this repo, though it still reflects the pre-pivot NL-intake flow — see the
decision log in [`betterrx-notes.md`](betterrx-notes.md) for what to change there.
