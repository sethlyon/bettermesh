# BetterRx Bounty — Kickoff & Q&A (Cleaned Transcript)

Cleaned from the raw auto-generated transcript (speaker-diarized, timestamped, low audio quality in places). Grammar and filler have been lightly smoothed for readability without changing meaning. Where the source text was garbled, I've made a best-guess translation and marked it `[uncertain: ...]`. A few stretches were pure transcription noise (ASR mis-hearing silence/crosstalk as speech) — those are called out separately at the end rather than presented as real dialogue, so they don't get mistaken for content.

This event covers three bounty pitches back-to-back (an AI growth/marketing bounty, a government-funding bounty, and the **BetterRx** bounty), followed by team announcements and a long BetterRx-specific deep-dive Q&A. Given the folder, the BetterRx sections (3, 4, 5) are probably what you care about most.

---

## 1. AI Growth/Marketing Bounty — 13:08–13:10
*Speaker `1d565164`, plus one unidentified speaker*

- Core framing: the number one thing that determines whether a customer stays is whether **they make money** — so the priority is **time to revenue** for autonomous businesses.
- Building blocks already available to riff on:
  - Meta Ads integration (Facebook/Instagram) — can generate images/video, run the ads, and report on performance.
  - Micro-adjustments to lower customer acquisition cost over time.
  - Lead generation via Google scraping or a lead database, feeding into cold outreach email sequences.
- The ask: get creative on (1) unique go-to-market approaches for the underlying businesses (e-commerce, construction, landscaping, car detailing, etc.), and (2) how the results/data feed back into the system so it learns what works and kills what doesn't.
- If your project works out and they like you, they'll consider hiring you onto the team.
- Audience clarified the scope: this is about **go-to-market plans for the individual client businesses**, not for your own team/company.

---

## 2. Government Funding Bounty — 13:10–13:16
*Speakers `c4657f92`, `74ccb980`, plus unidentified*

- Framed as a fast-growing, high-interest opportunity; mentioned doing a good job could lead to further work with federal agencies. [uncertain: the "Department of Transportation... Department of War" exchange around 13:11 reads as a joke/aside — audio unclear, not confident in the transcription here]
- Premise: HHS and other federal agencies have significant non-dilutive funding they want to deploy into "centers of innovation," but the money isn't reaching companies — **the bottleneck is discovery/paperwork, not lack of funding**.
- **The bounty**: build a tool that scrapes multiple government funding sources (NSF/America's Seed Fund, SBIR, federal procurement opportunities) and:
  1. Matches a company (based on its website/what it does) to the best-fit funding opportunities — "here are your 5 best matches."
  2. Auto-fills the applications/forms needed to apply, to reduce the effort required to get in front of reviewers.
- APIs exist for some sources (e.g., SBIR's API is open); others may require credentials — presenter said not to worry about building real authentication for gated sources, just flag them. [uncertain: transcript says "CSBI," almost certainly meant **SBIR**, referenced earlier in the same pitch]
- Prizes mentioned: **$200 gift card** for first, **$50 gift card** for second. [uncertain: exact placement/wording garbled in source]
- Closing: credited "Ben, the CEO" and a "principal" for the idea, then transitioned to the BetterRx pitch. [uncertain: this handoff exchange, ~13:16, was too garbled to transcribe reliably]

---

## 3. BetterRx — Company Introduction — 13:16–13:23
*Speaker `4509111c`*

- Thanked everyone who submitted for the bounty; noted the submissions included a lot of personal stories that resonated with the team.
- **The problem, told through a story**: a caregiver whose wife had a terminal illness for several years described the hardest part as "every night I go to sleep and I don't know if she's going to be there tomorrow." On top of that emotional weight, caregivers also have to track: *Where are the medications? Are they ordered? Delivered on time?* — logistics that shouldn't be on their plate.
- For the patient, hospice is meant to be a **dignified passing** — free of unnecessary pain, not complicated by medication logistics.
- BetterRx's founder had a personal loss that motivated the company: a story about a nurse unable to get medication delivered from the pharmacy in time, resulting in a patient dying while still waiting. **Mission: end suffering caused by medication-access delays.**
- Nurses/case managers were repeatedly described as "superheroes" for the effort they put in when the system fails — including personally tracking down medication.
- **The villain in this story is the PBM (Pharmacy Benefit Manager)** — described as an intermediary more focused on its own economics than getting medication to patients quickly, forcing nurses to scramble.
- BetterRx's product: software that eliminates the frantic manual phone-call process for getting medication to hospice patients. Framed as **operationally simple, not technically exotic** — the value is in simple, reliable workflows for a non-technical, high-turnover workforce.
- Positioning: healthcare broadly lags on tech adoption, and hospice lags even further within healthcare — yet BetterRx's product is comparatively simple and effective, which has let them help "millions of lives."
- **What's next — expanding into DME (Durable Medical Equipment)**: nurses don't just call frantically about medications, they call frantically about equipment too (e.g., a patient discharged into home hospice who needs a bed or oxygen tank immediately, not in a few days). Cited a "moral obligation" (a consultant's phrase) to extend their tech to reduce PBM/vendor friction here too.
- 10 teams were being selected for this bounty round — capped at 10 so each team gets adequate time to present. Anyone not selected was still invited to reach out with ideas.

---

## 4. Team Roster & Logistics — 13:24–13:35

- Presenting/answering for BetterRx across the session: **Todd**, **Peter** (CTO), **Eric Hemming** (President), and **Ben Cargis** (CEO) — named directly at 13:29 and 13:54. [uncertain: exact who-said-what attribution between Todd/Peter/Eric is not fully reliable in the diarization]
- An FAQ doc was emailed out in advance — attendees were asked to read it before the deep-dive Q&A, since it pre-answers most common questions.
- Logistics for the rest of the event:
  - No more scheduled programming for the day after this session — teams free to work from wherever.
  - Next day's session starts around **noon**; no need to arrive in the morning.
  - Venue for the next day is a different building across the highway (a "build.com" building). [uncertain: building name/street reference garbled — heard as "Dibby building" and a date-like "May 19th" that doesn't fit context, possibly a street number]
  - A BBQ was mentioned as part of the schedule.
  - Reminder to scan a QR code for platform credits if not already done, and a plug from a model-hosting sponsor to try their platform (custom/open-source model hosting) for the competition or otherwise.
- BetterRx doesn't normally use Slack (Teams is their default) but set up a dedicated Slack for this event given the number of teams.
- Support availability: reachable most of the day (team is traveling for the event), slower around dinner, and **not** available late at night (no 2am responses) — questions asked overnight get picked up the next morning.
- **Q&A policy**: they intend to answer every Slack question **publicly** rather than privately, so the answer benefits every team, not just the one who asked.

---

## 5. BetterRx Deep-Dive Q&A — 13:35–13:54
*Primary answerer: Speaker `59d538dd` (technical depth suggests this is Peter, the CTO), with questions from teams `e6dca111`, `6f956d2c`, and others*

**Business model**
- BetterRx sells software to **hospices** (the client); on the other side, they run a **marketplace with a pharmacy network** that actually fills and delivers medications.
- Software handles claims adjudication, ordering, and medication management.
- Hospice is a **very cost-constrained industry** — no relief from government reimbursement, margins keep getting thinner — which shapes what's valuable to build.

**"Guardrails" concept**
- Rather than requiring clinicians to make the perfect decision every time, the system encodes a hospice's own "philosophy of care" and nudges users toward the right choice by default.
- This matters because of **high staff turnover** — the guiding design principle: *design for a user who is always new, and assume the least tech-savvy possible user* ("think of your mom, or your grandmother's least technical friend").
- Concrete example: if a clinician would default to a higher-cost medication, the system can substitute a lower-cost, clinically-equivalent one automatically.

**Extending guardrails to DME**
- Same philosophy applies to durable medical equipment. No DME-specific technology in the market impressed the presenter yet.
- The competitive edge is expected to come from **visibility** (can a clinician see equipment location/status, place an order, check inventory in real time — an "Amazon-like" experience) and from **real, visible pricing** — BetterRx claims to have been first in their industry to show real prices in-system (two years ago), which doctors found genuinely valuable since they'd previously had no visibility into cost.
- Pricing caveat from a question: pricing is far murkier outside Medicare/hospital settings — private insurance pricing is opaque and out of BetterRx's control.

**Three decision factors clinicians weigh when ordering**
1. **Availability** — is it in stock, and when can it be delivered.
2. **Price** — comparable to comparing options in an Amazon-style checkout.
3. **Speed** — which option gets there faster.
- Today, hospices are typically locked into one primary vendor (and maybe a backup), limiting real choice — BetterRx wants to open that up with genuine vendor selection.

**Why this matters reputationally**
- If a vendor fails to deliver on time, **the hospice takes the reputational hit, not the vendor** — most patients/families never know who the pharmacy or DME vendor actually was.
- This feeds into **CAHPS scores** [transcript said "cap scores" — this is almost certainly CAHPS, the hospice satisfaction survey used in public ratings], which are damaged by things like late deliveries or equipment arriving in poor condition (a wheelchair that wasn't cleaned was cited as a real example).
- Open gap acknowledged by the presenter: they don't have full visibility into what happens **on the vendor's receiving end** when an order comes in, or exactly how integration will work (possibly a system-to-system integration, possibly something lighter like a magic link) — teams were explicitly told to make and defend their own reasonable assumptions here, since "your knowledge here is going to be about as good as ours."

**User personas** (in response to "who is actually using this — the prescriber, or hospice ops?")
1. **Admissions nurse** — places the initial order for something already prescribed (e.g., oxygen tank, hospital bed) when a patient is admitted to hospice.
2. **Case manager** — visits patients regularly and orders equipment/medication as a patient's condition progresses (e.g., needing a wheelchair later on). Gets the prescription via the physician, often surfaced through an **IDT meeting** (interdisciplinary team meeting where nurses and physicians review a patient), then places the order in the platform.
3. **Director of nursing** — oversees admissions nurses and field nursing staff; approves higher-cost decisions and owns reporting that balances cost and quality of care.
- Confirmed: yes, it does happen that a nurse identifies a need first and has to get the doctor to prescribe it before ordering.

**Data/EMR context**
- Orders originate in the hospice's **EMR** (electronic medical record) — the source of truth for prescriptions, restrictions, and patient info.
- DME is **far less regulated** than medication — nurses often act on a standing order/protocol from a doctor ("anytime this symptom appears, go ahead and order X") rather than needing a fresh prescription each time. Controlled substances are a separate, stricter case.
- DME pricing is **set by vendors**, not insurance or government — so vendor-specific pricing should be modeled in the system alongside ordering.
- Major EMRs in this space: **Epic** (large hospital-system EMR, less relevant here), and for home hospice specifically: **Matrix Care**, **HomeCare HomeBase**, and (likely) **WellSky** [transcript garbled as "Well, Scott" — WellSky is a well-known home-health/hospice EMR vendor and the near-certain intended name].
- BetterRx already has live patient data flowing into their system today (for medication; not yet for DME) — teams don't need to build this integration themselves and can use existing mock/patient data.

**Device/platform**
- Field staff (nurses visiting homes) mostly use tablets/phones; admissions and office-based staff use desktop/laptop.
- BetterRx's existing product is a **web-based app** — the expectation is a responsive web app that works across desktop and mobile, not a native app.

**Delivery lifecycle — including pickup, not just drop-off**
- A question raised the "pickup" side of DME: equipment (e.g., a hospital bed) that lingers in a home after it's no longer needed.
- Confirmed as an important, easy-to-overlook part of the problem: when a patient passes, the hospice **continues paying for the equipment** every day it sits in the home uncollected — the target is pickup **within 24 hours**.
- Hospices generally don't stock DME themselves (most hospice care happens in the patient's home, not a facility) — nurses may carry small "comfort kits" of basic over-the-counter medication in their car, but not equipment like beds.

**One more operational nuance**
- Hospice admission can happen "backwards" — a nurse may get a call and admit a patient before the paperwork catches up. The system should be built expecting that **care starts before paperwork is complete**, not the other way around.

---

## Notes on transcription quality

A handful of stretches in the raw transcript are not reliable dialogue — they read as classic speech-to-text hallucinations, produced when the audio was silent, pure crosstalk/applause, or otherwise unclear (this is a known failure mode of automatic transcription, not real spoken content):

- **13:31** — "For more information visit www.fema.gov" — has no connection to surrounding context; a known type of ASR hallucination.
- **13:33** — "ご視聴ありがとうございました" (Japanese for "Thank you for watching") — a very well-known Whisper-style hallucination that appears during silence.
- **13:34–13:35** and **13:52** — two long rambling, incoherent passages (starting "I am so happy to have some time for a month..." and "It was, it was a good time...") — almost certainly mis-transcribed crosstalk or background noise, not real speech. I did not attempt to "translate" these since there's no reliable signal to recover.
- **13:34** — "This video is made possible in this video..." — another stock hallucinated phrase.
- Scattered single-word/short lines ("Thank you," "So," "I," "Good.") throughout 13:27–13:35 are most likely applause, room noise, or brief crosstalk picked up between speakers, not substantive content.

Everything in sections 1–5 above reflects what I judged to be real spoken content, cleaned up and reorganized; anything I wasn't confident about is explicitly flagged inline with `[uncertain: ...]` rather than silently corrected.
