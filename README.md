# BetterMesh by BetterRX — hackathon prototype

Closed-network DME dispatch for hospices. FastAPI + HTMX, SQLite-backed.
Built for AI Builder Day (BetterRX bounty — DME Ordering and Visibility Challenge).

**Live:** [bettermesh.theslyon.com](https://bettermesh.theslyon.com)

Three fictional hospices, each with its own mock back-office site and a signed
login straight into BetterMesh:
[anchorpoint.theslyon.com](https://anchorpoint.theslyon.com) ·
[cedarridge.theslyon.com](https://cedarridge.theslyon.com) ·
[thistlemoor.theslyon.com](https://thistlemoor.theslyon.com)

See [`docs/pitch.md`](docs/pitch.md) for the full pitch and
[`docs/betterrx-notes.md`](docs/betterrx-notes.md) for the planning/decision log
(reasoning trail, open questions, and everything learned from the bounty FAQ and
kickoff Q&A — [`docs/bounty-faq.pdf`](docs/bounty-faq.pdf) and
[`docs/qa-transcript/`](docs/qa-transcript/)).

## What it does

- **Real system-to-system intake, not free text.** A hospice's own record system
  pushes an already-structured DME need straight into BetterMesh via
  `POST /webhook/pre-discharge-order` (a shared-secret webhook, not a login) — no
  parsing, matching how the pitch describes discharge-record integration actually
  working. `app/care_platform.py` is a mock stand-in for that hospice system: three
  differently-branded, login-free patient chart sites, each demoing a different
  journey (see below) against the exact same underlying functionality.
- **Signed SSO hand-off.** A link on a hospice's own site logs the visitor straight
  into their BetterMesh tenant account (`GET /sso`, `app/sso.py`) — no separate
  BetterMesh credentials to hand out for a demo.
- **Per-hospice tenant isolation.** Each hospice's BetterMesh account only sees its
  own orders; `casemanager` is the unrestricted account that sees the whole network.
  A hospice-scoped login also carries that hospice's logo/palette into BetterMesh's
  own UI.
- **Shared order board** with two role views (hospice case manager / DME dispatcher),
  behind real login (session-based).
- **Risk detection**: an order flags red when its ETA misses the discharge window.
- **Opportunity pool + accept**: unassigned and re-broadcast orders sit in a network
  pool; each vendor sees the ones they stock with a suggested ETA and a can-meet /
  would-miss signal, and pulls one by **accepting** it.
- **Tier-1 auto-routing**: an order skips the pool only when exactly one contracted
  vendor stocks that equipment and can meet the window — otherwise it's always an
  open pool decision, never an auto-push.
- **Re-broadcast**: a hospice releases an at-risk order back to the pool for a
  faster vendor to claim. **Cancel** is available for open (unassigned) orders, both
  from the board and via `POST /webhook/cancel-order`.
- **Best match recommendation**: the hospice board shows the top-ranked contracted
  vendor for each open/at-risk order — on-time delivery confidence first, price
  second.
- **Idempotent intake**: a caller-supplied `external_ref` on the pre-discharge
  webhook dedupes retries/double-clicks instead of fanning out duplicate orders.
- **Consent-on-file tracking**: whether the patient/family has consented to sharing
  their info with the fulfilling DME vendor, surfaced on the board when missing.
- **Outbound push notifications**: BetterMesh best-effort pushes status changes
  (accepted/delivered/pickup completed) back to the hospice's own system
  (`app/notifications.py`) — fire-and-forget, never blocks the triggering action.
- **Post-death pickup**: mark a patient deceased (from the board or via
  `POST /webhook/mark-deceased`) and pickup orders auto-generate (24h target),
  routed to the vendor that fulfilled the original. Idempotent per source order.
- **All Dispatches & Pickups**: a flat, filterable view of every order (patient +
  multiselect equipment-type filters), with clickable rows that jump to that
  patient's card on the main board.

Seeded with the six sample orders from the bounty brief, including DME-10305
(a STAT order whose current vendor misses the window) for the save demo.

## Three demo journeys, one system

Every hospice site has identical functionality — which journey you walk through is
just which patient/site you demo on, not a difference in what the system can do:

| Site | Patient | Journey |
|---|---|---|
| [anchorpoint.theslyon.com](https://anchorpoint.theslyon.com) | Miriam Castellano (PT-89112) | Routine pre-discharge dispatch |
| [cedarridge.theslyon.com](https://cedarridge.theslyon.com) | Walter Osei (PT-89204) | Mid-stay a-la-carte equipment order |
| [thistlemoor.theslyon.com](https://thistlemoor.theslyon.com) | Agnes Pruitt (PT-87950) | Mark deceased → watch pickup dispatch |

## How availability + pricing work

Each vendor has a synthetic profile in `app/models.py`: a `stock` set (which HCPCS
E-codes it carries), a `speed_min` (how fast it can arrive), and a `price` (flat
rate per delivery — DME pricing is vendor-set, not insurance-set, confirmed in the
kickoff Q&A). An order in the pool is an opportunity **only** to vendors that stock
it. The suggested ETA is `now + speed_min`, "can meet" is `suggested_eta <= target`,
and the hospice-side "best match" ranks candidates by (meets window, ETA, price) in
that order — confidence beats price, price only breaks ties. The vendor decides to
accept; the app never auto-pushes except in the narrow Tier-1 single-vendor case
above. This is the Tier 1 inventory signal from the pitch made concrete; a real
integration would replace the synthetic profile with a live inventory/ETA/pricing
feed.

## Run

```bash
cd bettermesh
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000 — you'll be redirected to `/login`. The mock hospice
sites are at `/care-platform/?hospice=<slug>` locally (no subdomain routing on
127.0.0.1), e.g. `/care-platform/?hospice=anchorpoint`.

## Deploy (Cloudflare Containers)

The app runs as-is (unmodified) inside a Cloudflare Container, fronted by a thin
Worker (`src/index.ts`) that routes every request — regardless of which domain it
came in on — to a single named container instance — the app's SQLite store and
login sessions need to live in one process, not be sharded per request. Requires
the **Workers Paid** plan (Containers isn't available on Free) and Docker running
locally to build the image.

```bash
npm install
npx wrangler secret put SESSION_SECRET   # paste a random value
npx wrangler secret put WEBHOOK_SECRET   # paste a random value
npx wrangler deploy
```

`wrangler.jsonc` binds `bettermesh.theslyon.com` plus the three hospice subdomains
as custom domains — Cloudflare provisions the DNS records automatically on first
deploy as long as the zone is on the same account as the Worker. First request
after a period of inactivity has a cold-start delay (container spinning up from
zero instances); subsequent requests are fast.

Environment variables (both required beyond local demo use):
- `SESSION_SECRET` — signs the login session cookie.
- `WEBHOOK_SECRET` — shared secret for the system-to-system API (the
  `/webhook/*` and `/api/*` routes a hospice's own system calls) and for signing
  the SSO hand-off link. Both fall back to an insecure dev default if unset.

### Demo accounts (local/demo only — not real credentials)

| Username | Password | Role |
|---|---|---|
| `casemanager` | `hospice123` | Hospice case manager (all hospices, unrestricted) |
| `anchorpoint` | `anchorpoint123` | Anchorpoint Hospice Partners case manager (tenant-scoped) |
| `cedarridge` | `cedarridge123` | Cedar Ridge Hospice & Home Care case manager (tenant-scoped) |
| `thistlemoor` | `thistlemoor123` | Thistlemoor Hospice case manager (tenant-scoped) |
| `dispatcher1` | `vendor1pass` | Sample Vendor 1 |
| `dispatcher2` | `vendor2pass` | Sample Vendor 2 |
| `dispatcher3` | `vendor3pass` | Sample Vendor 3 |

You generally won't need these directly — each hospice site's "Open BetterMesh"
link signs you straight in as that hospice's account.

## Demo flow

1. Open a hospice site, e.g. [anchorpoint.theslyon.com](https://anchorpoint.theslyon.com),
   and open that patient's chart (see the journey table above).
2. **Dispatch Equipment** (or **Order Equipment** for the a-la-carte journey) →
   pushes a structured order straight into BetterMesh via the pre-discharge
   webhook. The chart's "BetterMesh Status" panel polls and shows it live.
3. Click **Open BetterMesh** (or **View in BetterMesh**) → signs you straight into
   that hospice's tenant-scoped BetterMesh account, board pre-filtered/highlighted
   to that patient.
4. Log in as `casemanager` to see the whole network. Orders are grouped into *Needs
   attention* / *In progress* / *Completed*. **DME-10305** sits under Needs
   attention, flagged **At risk**, with a "Best match" line showing the top vendor
   recommendation.
5. Click **Re-broadcast to network** → it drops its vendor and returns to the pool
   as an open opportunity.
6. Log out, log in as `dispatcher3`. DME-10305 appears under **Open opportunities**
   marked **Can meet**. Click **Accept** → it moves to *My deliveries* with a
   committed ETA, and a status-update notification pushes back to the hospice site.
7. **Post-death pickup.** On [thistlemoor.theslyon.com](https://thistlemoor.theslyon.com)'s
   Agnes Pruitt chart, mark her Deceased → a pickup request auto-generates, routed
   to the vendor that delivered the original. Log in as that vendor to confirm it.
8. **All Dispatches & Pickups** (from the board toolbar) → filter by patient or
   equipment type, click any row to jump back to that patient's card.
9. **Reset demo** returns to the seeded state.

## Two roles

- **Hospice case manager** — orders grouped by attention; see vendor
  recommendations, re-broadcast or cancel at-risk/open deliveries, mark a patient
  deceased, browse the full dispatch/pickup history.
- **DME dispatcher** — vendor-scoped, three columns: **Open opportunities** (pool
  orders you stock, with accept), **My deliveries** (committed), **Pickup requests**
  (assigned to you).

## Structure

| Path | Role |
|------|------|
| `app/models.py` | Order dataclass, equipment catalog, vendor network + synthetic inventory/pricing |
| `app/store.py` | SQLite-backed order store, seeds the six sample orders |
| `app/dispatch.py` | Risk-triggered re-dispatch, vendor ranking, cancel, post-death pickup |
| `app/auth.py` | Demo account table (incl. per-hospice tenant accounts), session login/logout |
| `app/sso.py` | Signed hand-off from a hospice's own site into its BetterMesh account |
| `app/notifications.py` | Outbound push: BetterMesh → hospice system status updates |
| `app/care_platform.py` / `app/care_platform_data.py` | Mock hospice back-office sites (routes + synthetic patient/brand data) |
| `app/main.py` | FastAPI routes, webhook/API surface, HTMX partials |
| `app/templates/` | Board, dispatches, login, and mock-hospice-site UI |
| `docs/` | Pitch, planning notes, bounty brief, and kickoff Q&A source material |

## Notes for the build

- SQLite store resets to the seeded demo state on every restart/`/reset`, by
  design — a live pitch needs deterministic starting state.
- No PHI, no LLM calls, no external calls beyond BetterMesh's own outbound status
  notifications back to the mock hospice sites. All order/patient data is
  synthetic.
