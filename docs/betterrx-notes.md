# BetterMesh by BetterRX — Planning Context & Decision Log

Companion to [pitch.md](pitch.md) and the working prototype in [`../app/`](../app/). This
captures the *reasoning* behind the plan — the decisions, dead-ends, talking points,
and open questions — so nothing from the planning conversation is lost.

> Planning notes for the BetterRX DME bounty submission, published alongside the
> prototype in this repo.

---

## Where this stands

- **Bounty:** BetterRX — DME Ordering and Visibility Challenge ($10,000, limited to
  8 pre-selected teams).
- **Pre-selection form:** submitted.
- **What BetterRX actually is (confirmed, kickoff Q&A 2026-08-14):** BetterRX is
  *not* a hospice — it's a company that sells software **to** hospices, and on the
  other side runs a two-sided **marketplace with a pharmacy network** that fills
  and delivers medications (CTO, deep-dive Q&A, "Business model"). DME is not a
  speculative pivot for them; it's the **same existing business model** (software
  + marketplace, sold to the same hospice customer) extended into a second
  category. Productization isn't a stretch goal we're adding on top of a hackathon
  demo — it's the actual plan, confirmed directly by the company. This changes how
  confidently the productization sections below should be framed.
- **Product:** BetterMesh by BetterRX — closed-network DME dispatch with an opportunity
  pool vendors pull from, risk-triggered re-broadcast, and post-death pickup.
- **Prototype:** working FastAPI + HTMX app in [`../app/`](../app/), seeded with the
  brief's six sample orders. Hospice (kanban) + vendor-scoped dispatcher views.
  BetterRX navy/teal theme.

---

## Why BetterRX over the other bounties

- **Domain edge is rare and hard to fake.** Hospice owner next door to validate
  workflow + vouch for authenticity; Direct Supply background on the vendor/logistics
  side of medical equipment. We sit on *both* sides of the exact gap BetterRX wants
  closed.
- The problem is well-defined and interview-sourced, so a shallow solution gets
  spotted fast — which favors us, not hurts us.
- Higher reward ($10K vs $5K for MadeThis/GOED) and the domain maps to real
  experience rather than a generic agent build.
- Fallback if we don't get a BetterRX slot: **Government Opportunity Finder** (open,
  real public APIs, LLM-shaped judging). MadeThis/GOED are weaker fits for our edge.

---

## The idea, and how it evolved (the reasoning trail)

1. **Naive instinct — "Uber for DME":** broadcast every order to every vendor,
   dispatch the best. *Why it breaks:* Medicare Hospice Benefit reimbursement runs
   through pre-negotiated contracts tied to a specific vendor's NPI. You can't
   dispatch to an arbitrary vendor and have the claim clear. Inventory isn't fungible
   either — closest ≠ has-a-bed.
2. **The version that survives — closed-network dispatch:** the "network" is the 3–5
   vendors the hospice *already contracts with*. The brief confirms hospices keep 2+
   vendors per market as a manual fallback. We automate the fallback they already
   rely on. No new billing relationships, no compliance wall.
3. **Opportunity pull model (what the app actually does now):** orders sit in a
   network pool; each vendor sees the ones they stock with a suggested ETA and a
   can-meet / would-miss signal, and *accepts* to commit. No silent auto-push. This
   matches the "first to confirm gets it" language and reads as a real marketplace.
4. **Two-tier inventory:** Tier 1 (vendor shares live inventory) → deterministic,
   single-vendor-complete-preferred dispatch, no AI needed. Tier 2 (no inventory) →
   ETA-vs-window risk model + confirmation broadcast. Works day one with zero vendor
   integration; sharpens as vendors opt in. "Integrate your inventory, get preferred
   dispatch" is the incentive flywheel.
5. **Split fulfillment — talked about, deliberately NOT built.** If vendor A has 90%
   but no bed, split the bed line-item to vendor B as its own clean order (two clean
   claims, no inter-vendor physical handoff). Compliance story isn't demo-ready, so
   it's roadmap, not core.
6. **Integration-first intake — pivot away from NL order entry (2026-08-14):** the
   DME need already exists in BetterRX's discharge record — a physician's order or
   care plan line-item — so the case manager shouldn't have to re-describe it in
   natural language. A "Dispatch equipment" action on that existing record sends
   the already-structured order straight into BetterMesh. NL intake dropped: it
   assumed simple orders, assumed the person typing knew the patient number, and
   was the closest thing in the pitch to an AI-for-AI's-sake add-on. A manual
   fallback (a plain form, no AI) still covers the rare need not yet on the
   discharge record. See "Pre-discharge equipment dispatch" below.

---

## Pre-discharge equipment dispatch — the other trigger BetterRX already holds

- **Problem:** the earlier pitch had case managers re-typing an order in natural
  language, which assumes the DME need doesn't already exist as data anywhere and
  that whoever's placing the order has the patient number memorized. Neither is
  true — the need is already documented in BetterRX's discharge record.
- **What changes:** a "Dispatch equipment" action on the existing discharge record
  sends the already-structured need (patient ID, HCPCS E-code, target window)
  straight to BetterMesh, which immediately routes it through the existing Tier
  1/Tier 2 dispatch engine. This only changes how the order *arrives* — not how
  it's routed once it's in the network.
- **Why this beats NL intake:** no parsing, no ambiguity, no AI needed — the data
  was never unstructured to begin with. It also mirrors the death trigger exactly:
  BetterRX already holds the signal, BetterMesh just subscribes to it. Same wiring
  options (BetterRX-native vs EMR-sourced), same open question (real-time vs
  end-of-day / batch).
- **AI verdict:** none needed for intake or dispatch. The problem is logically
  simple; the real implementation risk is integration (getting the event out of
  BetterRX/EMR reliably) and DME vendor adoption (getting vendors onto BetterMesh
  at all) — which is why launch should be a paired pilot: one hospice's BetterRX
  wired up, that hospice's actual contracted vendors onboarded, prove the mesh
  holds before generalizing.

---

## Post-death pickup — the strongest strategic thread

- **Problem (from the brief):** pickup is triggered by a phone call after a death.
  When it's slow, a grieving family stares at equipment they no longer need, the
  hospice takes the blame, and the hospice pays for extra equipment-days.
- **Now directly confirmed, not just inferred (kickoff Q&A):** "when a patient
  passes, the hospice continues paying for the equipment every day it sits in the
  home uncollected — the target is pickup within 24 hours." This resolves who
  bears the cost of a delayed pickup (the hospice, per equipment-day) and gives us
  a sourced SLA instead of a guessed one — `dispatch.py` now targets 24h, not the
  earlier placeholder 8h. Also confirmed: hospices don't stock DME themselves (care
  happens in the home, not a facility), so there's no self-fulfillment path — the
  vendor network is the only source of both delivery and retrieval.
- **What BetterMesh changes:** removes the *notification* delay — a status change fans out
  a pickup order instantly, with a timestamp both sides are accountable to. It does
  not make the truck faster; claim the notification win, not a logistics miracle.
- **The killer productization insight:** BetterRX is a hospice *medication* platform,
  so a death is already a first-class event in their workflow (meds stop, controlled
  substances must be reconciled/disposed). **BetterRX already holds the trigger, not
  just the buyer.** BetterMesh reuses the death event they already process for meds to
  fire DME pickup — one signal, currently unused for logistics.
- **Wiring options:** BetterRX-native (fastest, no new EMR integration) vs
  EMR-sourced (HCHB/Axxess/WellSky/MatrixCare, the system of record). Open question:
  is the death event real-time in BetterRX or end-of-day? Real-time makes "instant
  pickup" airtight; if it lags, trigger off the EMR.

---

## Productization thesis (the SaaS pitch to BetterRX)

- **Not a hypothetical extension — the same model, confirmed.** BetterRX already
  runs exactly this two-sided structure for medication: software sold to hospices
  on one side, a marketplace/pharmacy network fulfilling on the other. DME is the
  same shape, second category, same buyer. This is worth saying plainly in the
  pitch instead of hedging with "could become a SaaS line."
- Adjacent to their wedge: same buyer (hospice), same moment (discharge + death),
  natural second product beyond medication.
- They already have the customer *and* both data signals (the equipment need on
  the discharge record, and the death event).
- **Confirmed pain that justifies urgency:** "if a vendor fails to deliver on time,
  the hospice takes the reputational hit, not the vendor" — feeds CAHPS scores
  directly (late delivery, equipment arriving in poor condition — an uncleaned
  wheelchair was their own cited example, independently matching the bounty FAQ's
  Q9 equipment-condition pain point). Two separate sources now name the same gap.
- **"Guardrails" is their stated design philosophy, not just ours.** Rather than
  requiring a clinician to make the perfect call every time, the system encodes
  the hospice's own philosophy of care and nudges toward the right default —
  driven by high staff turnover ("design for a user who is always new, assume the
  least tech-savvy possible user"). BetterMesh's risk flag + best-match
  recommendation is a DME-side instance of exactly this pattern: don't require the
  case manager to compare vendors manually, surface the right default.
- **Three factors clinicians actually weigh** (their words): availability, price,
  speed. Today hospices are typically locked into one primary vendor (maybe a
  backup) with no real choice — BetterRX explicitly wants to open that up. This is
  direct validation of the closed-network multi-vendor model and the price+ETA
  "best match" ranking already built.
- **DME pricing is vendor-set**, not insurance/government-set (unlike medication,
  where Medicare/hospital pricing is at least somewhat visible) — confirms
  per-vendor pricing needs to be modeled in the system, not assumed uniform.
- Two-sided monetization: hospices pay for visibility+reliability; vendors pay/upsell
  for preferred dispatch + inventory integration, and later for demand forecasting
  once network volume exists.
- Low starting lift: Tier 2 needs nothing from vendors; convert to Tier 1 over time.
- Defensible data asset: every order/ETA/outcome becomes proprietary reliability data
  (vendor scorecards, benchmarks) no single vendor or EMR can replicate.
- Rides existing EMR integration layers rather than rip-and-replace.

---

## Kickoff Q&A digest (2026-08-14 transcript, sections 3-5)

Source: cleaned transcript of the BetterRX kickoff pitch + deep-dive Q&A
(`Bounties/BetterRX/QA Session Transcript (cleaned).md`). Items above are folded
into their relevant sections already; this is what's left over.

- **Team:** Todd, Peter (CTO — primary technical answerer in the Q&A), Eric
  Hemming (President), Ben Cargis (CEO).
- **Origin story (usable talking point):** founder's motivating loss — a nurse
  unable to get medication delivered from the pharmacy in time, patient died
  waiting. Mission stated as "end suffering caused by medication-access delays."
  The PBM (Pharmacy Benefit Manager) is framed as the villain — an economics-first
  intermediary that forces nurses into frantic manual phone-call workarounds.
  DME is explicitly framed as the same fight, second category: nurses call
  frantically about equipment too, not just medication. Worth echoing this framing
  live ("BetterMesh extends the same mission you already have to equipment") since
  it's their own language, not ours.
- **Personas we're collapsing into one "hospice case manager" role for the demo:**
  1. *Admissions nurse* — places the initial order for something already
     prescribed at admission (oxygen tank, hospital bed).
  2. *Case manager* — orders equipment as a patient's condition progresses,
     prescription surfaced via an IDT (interdisciplinary team) meeting. This is
     the persona BetterMesh's single hospice login currently models.
  3. *Director of nursing* — oversees admissions/field nursing, approves
     higher-cost decisions, owns cost/quality reporting.
  Also confirmed: a nurse can identify a need *before* the doctor formally
  prescribes it — ordering doesn't always wait on paperwork.
  Worth stating explicitly as scope: "we modeled the case manager persona; the
  other two are the same underlying board with different permission/approval
  scope, not a different product."
- **EMR confirmation status:** the kickoff Q&A directly named **HomeCare
  HomeBase** (= HCHB), **MatrixCare**, and **WellSky** as the relevant home-hospice
  EMRs. It did **not** mention Axxess — that's our own addition from outside
  research, not something BetterRX confirmed. Keep saying it (reasonable, it's a
  real player in the space) but don't present it as confirmed the way the other
  three now are.
- **DME regulatory nuance:** DME is far less regulated than medication — nurses
  often act on a standing order/protocol from a doctor rather than needing a fresh
  prescription every time (controlled substances remain the strict exception).
  Supports the pre-discharge dispatch pivot: the trigger doesn't always require a
  brand-new physician order in the moment.
- **"Care starts before paperwork" (explicit design principle from BetterRX):** a
  hospice admission can happen "backwards" — a nurse admits a patient before the
  paperwork catches up. Build expecting care to start before records are fully
  coded, not the other way around. This is a live tension worth naming with the
  pre-discharge dispatch pivot: if the discharge record isn't fully structured
  yet, the "read existing structured data" trigger may not have anything to read
  yet — which is exactly why the manual fallback form needs to stay real, not a
  vestigial "rare case" path.
- **Platform confirmation:** field nurses mostly use tablets/phones; office/admin
  staff use desktop. BetterRX's existing product is a **responsive web app**, not
  a native app — matches our stack choice (FastAPI + HTMX, no native build)
  exactly, no change needed, just now a cited decision instead of a default.
- **Q&A logistics note:** BetterRX answers every Slack question publicly so all
  teams benefit — if we ask something in Slack, assume every other team sees the
  answer too; no private edge from asking first.

---

## Naming decision log

Final: **BetterMesh by BetterRX**.

- *Mesh* names the dispatch model itself — a closed mesh of the hospice's own
  contracted vendors, not a single point-to-point vendor relationship. When one
  link is about to fail, the order re-routes to another node already in the mesh.
- "by BetterRX" keeps the parent brand as the endorsing house — a new product line,
  not a rebrand.
- Rejected along the way: BetterNetwork (generic), BetterTX (messes with their brand
  too much), BetterRx(Tx) (parentheses unsayable/footnote-like), NetworkRx (early
  working name), NetTx (Net=vendor network, Tx=transmit — dropped once "Mesh" read
  clearer and didn't need the receive/transmit wordplay to land).

---

## Draft answers we prepared (reuse on the day)

**"What excites you about this bounty?"**
> The problem is real and the stakes are high — equipment delays around a patient's
> death aren't a UX issue, they're a human one. I also happen to have a hospice owner
> next door, so I can build something that actually fits how these workflows run
> instead of guessing at them.

**"Was anything missing from the brief you'd want answered Friday?"**
> Is there a DME vendor involved who could speak to their side of this workflow? Most
> of the details focus on the hospice experience, and a good solution needs to work
> for both parties — understanding how DME vendors currently receive and track orders
> would shape the architecture pretty significantly.

---

## Demo one-liners / talking points

- "Today, pickup waits on a phone call nobody's incentivized to make quickly. BetterMesh
  makes the EMR's existing deceased-status change *be* the pickup order — instantly,
  with a timestamp both sides are accountable to. We don't make the truck faster; we
  delete the hours before anyone even knew to send it."
- "BetterRX already sits in the death moment for medications. BetterMesh extends that same
  trigger to equipment — same event, adjacent problem, no new data capture."
- "It's not a prettier portal. It changes what happens when a delivery is about to
  fail — the exact moment the hospice currently has no leverage."
- AI honesty: the whole primary application is deterministic rules — intake is an
  integration read, dispatch is a lookup, risk detection is a threshold. We say so.
  AI's real, honest use is a roadmap item on the vendor side (demand forecasting
  from network dispatch volume), not anywhere in the MVP.

---

## Open questions to confirm Friday (with the neighbor / BetterRX)

**Resolved — two independent sources now agree:**
- ~~Is there a DME vendor we can talk to?~~ **No** (bounty FAQ Q1: no vendor/dispatcher
  access, before or during). Independently reinforced by the CTO in the kickoff
  Q&A: BetterRX doesn't have full visibility into the vendor's receiving end
  either, or the exact integration mechanism (system-to-system vs. a lighter
  magic-link) — "your knowledge here is going to be about as good as ours," teams
  told explicitly to make and defend reasonable assumptions. Vendor-side design
  should lean toward the FAQ's own stated baseline (Q3): no-login, email/SMS
  magic-link confirmation, portal as a stretch goal only.
- ~~Who pays for a delayed pickup, and what's the SLA?~~ **Hospice pays per
  equipment-day it sits uncollected; target is pickup within 24h** (kickoff Q&A —
  see Post-death pickup section above). `dispatch.py` now reflects the 24h figure.

**Still open:**
1. When a primary vendor is going to be late, what does a hospice *actually* do today?
   Does risk-triggered re-dispatch match reality?
2. Are all contracted vendors equally billable for any order, or are there per-vendor
   equipment/coverage limits that constrain who a broadcast can reach?
3. Does the death event (and the pre-discharge equipment-need event) land in
   BetterRX in near-real-time or end-of-day/batch? Neither the FAQ nor the kickoff
   Q&A pinned this down — it's confirmed the data *exists*, not confirmed it's
   fast enough for the "instant" framing to be literally true.
4. Where does the DME need actually live in BetterRX today — a coded order
   (HCPCS-mappable) on the discharge record, or free text in a care plan? Matters
   for whether the pre-discharge dispatch trigger is a clean data read or still
   needs a mapping step somewhere.

---

## Prototype status (what's built vs roadmap)

Built and smoke-tested:
- Shared order model + six seeded sample orders (now-relative times so at-risk always
  holds), persisted to SQLite (was in-memory-only at the 2026-08-14 pivot writeup).
- Hospice kanban: Needs attention / In progress / Completed.
- Opportunity pool + vendor accept (pull model), stock + speed availability.
- Risk detection + hospice re-broadcast to network.
- Vendor-scoped dispatcher: opportunities / my deliveries / pickups.
- Post-death pickup auto-generation routed to the fulfilling vendor, now targeting
  the confirmed 24h SLA (was a placeholder 8h).
- Session-based login (hospice case-manager account + one dispatcher account per
  vendor), replacing the earlier role-toggle. Not in the original MVP scope, but
  built ahead of the pivot writeup above — worth weighing against the FAQ's stated
  judging weight (hospice side > vendor side, Q3) if time runs short elsewhere.
- **"Best match" vendor recommendation** on the hospice board for open/at-risk
  orders: ranks contracted vendors by on-time confidence first, price second
  (`dispatch.rank_candidates_for`) — directly validated after the fact by the
  kickoff Q&A's "availability, price, speed" framing and the vendor-locked-in
  pain point.
- NL order intake, now a real LLM call (Claude, via `nlp.py`) rather than the
  regex parser this section originally described. **Still pending the re-scope
  below:** per the 2026-08-14 pivot, this should become the manual-fallback path
  once pre-discharge dispatch exists, not stay the primary intake route — that
  swap hasn't happened yet, so the app's primary path and the pitch's primary path
  currently disagree.
- BetterRX navy/teal theme, low-radius cards.

Not yet built — next up for the pivot:
- Pre-discharge dispatch trigger (mocked BetterRX webhook → order created directly,
  bypassing the manual form as the primary path). This is the biggest gap between
  what pitch.md now describes and what the app actually does.

Roadmap (say it, don't build it):
- Split / multi-vendor fulfillment (compliance).
- Real eRx/EMR webhook integration (mock the shape + diagram).
- AI-driven vendor inventory demand forecasting — needs live network volume that
  doesn't exist until after launch.
- EMR deceased-status webhook as the real pickup trigger.
