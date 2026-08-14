# BetterMesh by BetterRX — hackathon prototype

Closed-network DME dispatch for hospices. FastAPI + HTMX, SQLite-backed.
Built for AI Builder Day (BetterRX bounty — DME Ordering and Visibility Challenge).

**Live:** [bettermesh.theslyon.com](https://bettermesh.theslyon.com)

See [`docs/pitch.md`](docs/pitch.md) for the full pitch and
[`docs/betterrx-notes.md`](docs/betterrx-notes.md) for the planning/decision log
(reasoning trail, open questions, and everything learned from the bounty FAQ and
kickoff Q&A — [`docs/bounty-faq.pdf`](docs/bounty-faq.pdf) and
[`docs/qa-transcript/`](docs/qa-transcript/)).

## What it does

- **Shared order board** with two role views (hospice case manager / DME dispatcher),
  behind real login (session-based, one account per hospice/vendor).
- **Risk detection**: an order flags red when its ETA misses the discharge window.
- **Opportunity pool + accept**: unassigned and re-broadcast orders sit in a network
  pool; each vendor sees the ones they stock with a suggested ETA and a can-meet /
  would-miss signal, and pulls one by **accepting** it. No auto-assignment.
- **Re-broadcast**: a hospice releases an at-risk order back to the pool for a
  faster vendor to claim.
- **Best match recommendation**: the hospice board shows the top-ranked contracted
  vendor for each open/at-risk order — on-time delivery confidence first, price
  second — visibility the hospice doesn't have today.
- **Post-death pickup**: mark a patient deceased and pickup orders auto-generate
  (24h target), routed to the vendor that fulfilled the original.
- **NL order intake**: a real LLM call (Claude) parses free text like "hospital bed
  for PT-88421 by tomorrow 2pm" into a structured order.

Seeded with the six sample orders from the bounty brief, including DME-10305
(a STAT order whose current vendor misses the window) for the save demo.

## How availability + pricing work

Each vendor has a synthetic profile in `app/models.py`: a `stock` set (which HCPCS
E-codes it carries), a `speed_min` (how fast it can arrive), and a `price` (flat
rate per delivery — DME pricing is vendor-set, not insurance-set, confirmed in the
kickoff Q&A). An order in the pool is an opportunity **only** to vendors that stock
it. The suggested ETA is `now + speed_min`, "can meet" is `suggested_eta <= target`,
and the hospice-side "best match" ranks candidates by (meets window, ETA, price) in
that order — confidence beats price, price only breaks ties. The vendor decides to
accept; the app never auto-pushes. This is the Tier 1 inventory signal from the
pitch made concrete; a real integration would replace the synthetic profile with a
live inventory/ETA/pricing feed.

## Run

```bash
cd bettermesh
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000 — you'll be redirected to `/login`.

## Deploy (Cloudflare Containers)

The app runs as-is (unmodified) inside a Cloudflare Container, fronted by a thin
Worker (`src/index.ts`) that routes every request to a single named container
instance — the app's SQLite store and login sessions need to live in one process,
not be sharded per request. Requires the **Workers Paid** plan (Containers isn't
available on Free) and Docker running locally to build the image.

```bash
npm install
npx wrangler secret put SESSION_SECRET      # paste a random value
npx wrangler secret put ANTHROPIC_API_KEY   # optional, enables live LLM intake
npx wrangler deploy
```

`wrangler.jsonc` binds `bettermesh.theslyon.com` as a custom domain — Cloudflare
provisions the DNS record automatically on first deploy as long as the zone is on
the same account as the Worker. First request after a period of inactivity has a
cold-start delay (container spinning up from zero instances); subsequent requests
are fast.

Optional environment variables (see `.env.example` at the repo root's parent
workspace, or just export directly):
- `ANTHROPIC_API_KEY` — enables real LLM-based NL intake. Without it, `/orders`
  degrades gracefully to a "could not parse" message rather than crashing.
- `SESSION_SECRET` — signs the login session cookie. Falls back to an insecure
  dev default if unset; set a real value outside local demo use.

### Demo accounts (local/demo only — not real credentials)

| Username | Password | Role |
|---|---|---|
| `casemanager` | `hospice123` | Hospice case manager |
| `dispatcher1` | `vendor1pass` | Sample Vendor 1 |
| `dispatcher2` | `vendor2pass` | Sample Vendor 2 |
| `dispatcher3` | `vendor3pass` | Sample Vendor 3 |

## Demo flow

1. Log in as `casemanager`. Orders are grouped into *Needs attention* / *In
   progress* / *Completed*. **DME-10305** sits under Needs attention, flagged
   **At risk**, with a "Best match" line showing the top vendor recommendation.
2. Click **Re-broadcast to network** → it drops its vendor and returns to the pool
   as an open opportunity.
3. Log out, log in as `dispatcher3`. DME-10305 appears under **Open opportunities**
   marked **Can meet**. Click **Accept** → it moves to *My deliveries* with a
   committed ETA.
4. Log back in as `casemanager` — DME-10305 is now under *In progress*, no longer
   at risk.
5. **Post-death pickup.** In *Mark deceased*, enter `PT-87950` → a pickup request
   appears, routed to the vendor that delivered the original. Log in as that
   vendor to confirm it.
6. **NL intake.** Type `STAT oxygen for PT-88999 by tomorrow 9am` → new order lands
   in the pool as *Awaiting vendor*, open for a stocking vendor to accept.
7. **Reset demo** returns to the seeded state.

## Two roles

- **Hospice case manager** — orders grouped by attention; place orders in natural
  language, see vendor recommendations, re-broadcast at-risk deliveries, mark a
  patient deceased.
- **DME dispatcher** — vendor-scoped, three columns: **Open opportunities** (pool
  orders you stock, with accept), **My deliveries** (committed), **Pickup requests**
  (assigned to you).

## Structure

| Path | Role |
|------|------|
| `app/models.py` | Order dataclass, vendor network + synthetic inventory/pricing |
| `app/store.py` | SQLite-backed order store, seeds the six sample orders |
| `app/dispatch.py` | Risk-triggered re-dispatch, vendor ranking, post-death pickup |
| `app/auth.py` | Demo account table, session login/logout |
| `app/nlp.py` | LLM-based NL order intake (Claude) |
| `app/main.py` | FastAPI routes + HTMX partials |
| `app/templates/` | Board + login UI |
| `docs/` | Pitch, planning notes, bounty brief, and kickoff Q&A source material |

## Notes for the build

- SQLite store resets to the seeded demo state on every restart/`/reset`, by
  design — a live pitch needs deterministic starting state.
- `nlp.parse_order` is the seam where the LLM call lives, isolated from the rest
  of the app; the return shape never changed, so nothing downstream needed to.
- No PHI, no external calls beyond the Anthropic API when a key is configured.
  All order/patient data is synthetic.
