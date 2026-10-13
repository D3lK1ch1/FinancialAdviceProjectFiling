# Ground Truth — what this system does (engineer's version)

*Written 2026-09-29 from Delia's own statement of the project. If a PR, issue, or other doc
disagrees with this file, stop and resolve the disagreement. Don't quietly follow the other doc.*

## The system in one paragraph
A document arrives. The system works out **what kind of document it is** and **which client
it belongs to**. If it is at least **90% certain of both**, it files the document into that
client's folder. If not, it shows a **popup** with its best guess (document type and where
it would file it). The user **accepts**, or **rejects** and then either tells the system
what the document is and why, or files it by hand. Every change is recorded in a
**tracking log**. Everything runs **locally**.

## The pipeline, as software
```
file in
  → read text                         (parser.py)
  → is this an advice document at all? (scope_gate.py)
  → document type + confidence         (classifier.py, rules from knowledge_base.json)
  → client + confidence                (not built — GH#6)
  → both >= 0.90 ?
        yes → file to  <Surname>, <First name>/   and log it   [superseded 13 Oct: always popup, see Q7]
        no  → popup: "I think this is <type> for <client>, filed at <path>"
                 accept → file there, log it
                 reject → user gives correct type/client + a reason → file there, log it
                        → or user files it manually → log it
```

## Rules to hold on to
1. **Filing key = client name, surname then first name.** The point of the tool is that a
   document never ends up in the wrong client's folder. A wrong client is the worst possible
   failure.
2. ~~**90% threshold covers both the type and the client.**~~ **Superseded 13 Oct 2026 (Q7):**
   a person confirms every document — type, client, stage and new name — whatever the
   confidence. Nothing is ever filed automatically.
3. **The confidence has to be real.** An LLM that says "0.95" is only reporting its own
   opinion. The number has to be checked before the 90% rule means anything (PR #37).
4. **Reject is never a dead end.** The user can correct it (type, client, reason), or they
   can file it manually. Both routes get logged.
5. **Every change is logged:** what the system proposed, what the user did, who did it,
   when, and why (on a reject).
6. **Local only.** Nothing gets uploaded to cloud storage at this stage.

## How "tell the model" works in this codebase
A correction does two things:
- **Now:** the document gets filed where the user said.
- **Later:** the correction is saved to the failure log. A person reviews it and updates
  `knowledge_base.json` (keywords/hints), which improves recognition next time. The model's
  weights are never retrained automatically. That keeps every rule change visible and
  reversible (CLAUDE.md ground rules 1 and 6).

## Reminder: the financial-planning words are data, not logic
The document names and keywords below only matter for one thing: **helping the model
recognise a document so it gets filed correctly.** You don't need to understand the
advice law behind them. To you they are labels, plus the text patterns that point to
each label. They live in `knowledge_base.json`, never in Python.

| Label (id) | Plain meaning | Words that point to it |
|---|---|---|
| `soa` | The main advice document | "Statement of Advice", "SOA" |
| `roa` | Short follow-up advice document | "Record of Advice", "ROA" |
| `authority_to_proceed` | Client's signed "go ahead" | "Authority to Proceed", "Authority to Implement", "Client Authorisation" |
| `fsg` | The firm's "about us" brochure | "Financial Services Guide", "FSG" |
| `pds` | A product's brochure | "Product Disclosure Statement", "PDS" |
| `fact_find` | Client information form | "Fact Find", "Client Data Form" |
| `risk_profile` | Risk questionnaire | "Risk Profile", "Risk Tolerance Questionnaire" |
| `file_note` | Adviser's meeting notes | "File Note", "Meeting Note" |
| `fee_disclosure_statement` | Yearly fee statement | "Fee Disclosure Statement", "FDS", "Ongoing Fee Consent" |

A **client review** is a meeting, not a document type. It usually produces some of the
documents above (a file note, an ROA, a fee statement).

## Settled domain answers
- **ROA sub-types: three, not four** (confirmed 2026-09-29; the fourth was the same one counted
  twice). The model reads these from the body text, not the title:
  1. `further_advice`: a follow-up to an earlier SOA for the same client, where nothing important
     has changed. Covers "no change" reviews when the client already has an SOA.
  2. `no_buy_sell`: doesn't recommend buying or selling anything, **and** the adviser is paid
     nothing for it.
  3. `small_investment`: advice about an investment of $15,000 or less.
  "Hold / no action" isn't a separate sub-type. It describes what the advice says, and it
  falls under 1 or 2.
  - **Where this comes from:** the three-type model and its details ("adviser paid nothing",
    "$15,000 or less") came out of a Claude-assisted discussion with the domain partner, based
    on ASIC's INFO 266 and the legislation. It hasn't been checked against real firm documents.
    Only type 1 has real sample text (GH#33, GH#35). Treat types 2 and 3 as unverified.
  - **2026-09-29:** the partner hasn't studied types 2 or 3, so there's no domain knowledge and
    no real examples to build from. **Build rule:** the model only recognises type 1 (further
    advice). Any ROA that isn't clearly type 1 goes to the popup for a human to confirm. Don't
    build detection for types 2 and 3 unless a real example turns up.
- **Clients that aren't a person** (confirmed 2026-09-29):
  - **Trust:** the document says "Trust" or "Trustee".
  - **Company:** the document says "Company", or more likely the name ends in "Pty Ltd".
  - **Anything else** (other entity wording, mixed signals) goes to a human. Never guess.
  - **Matching ignores capitals:** "pty ltd", "PTY LTD" and "Pty Ltd" are all the same match.
    These words go in `knowledge_base.json` (GH#6 `client_model`), not in Python.
- **FSG and PDS** (confirmed 2026-09-29):
  - **A copy goes in each client's folder.** It is the proof that the client was given it.
  - **The master copy** is filed **manually** in a shared folder ("Base docs" / "Document
    templates"; name not final). These come from the firm or a product provider, so they
    aren't unique to any client. The tool doesn't file masters.
  - Engineering consequence: an FSG/PDS has no client name inside it, so the client has to
    come from **outside the document** (see engineer question below).

## Known differences from existing docs (resolve, don't ignore)
| Topic | This file | Elsewhere | Status |
|---|---|---|---|
| Threshold | 90% for everything | `review_policy`: 0.90 for every type (#50) | **Resolved 2026-10-02.** Matches |
| Folder levels | Client (`Surname, First name`) | #47 Client → Advice event; `settings.filing_mode` has `client_event` and `flat` (#51, flat not built yet) | **Resolved 9 Oct 2026.** Two layers: client folder, then an event folder named `YYYY-MM — <subject>`, never after one document such as "[SOA]". The stage is shown on each document, not as a folder (PR #58) |
| Popup actions | Accept / Reject (+ correct or manual) | SYSTEM.md: Approve / Edit / Reject | Same idea. "Reject + correct" = Edit |
| The "why" on a reject | Tell the model what it is and why | `review_policy.correction_reasons`: pick one of six codes, **no free text** (#43) | **Resolved by design.** A free-text box is where staff type a client's name, and the failure log is shared. The "speech bubble" is a pick-a-reason list |
| Who can accept | "The user" | `approval_policy` (#54): only an adviser (own clients, for SOA/ROA/ATP/FDS) or compliance may approve; admin and paraplanner can edit, not approve | **Added 2026-10-02**, decided by Bella. The tool now has roles |
| Blocking flags | Not in ground truth | `approval_policy.flag_effect_by_rule` (#54): 4 hard stops only compliance can clear (ATP without advice, risk mismatch, fact find after SOA, bundle); the rest are warnings | **Added 2026-10-02** |
| Tracking log | Every change | Failure log records reviewer verdicts (#40, #43), not yet every action with model version (#7) | Open. Need an audit log as well as the failure log |

## Domain partner
She has **no access to real client documents**, and they would be highly confidential anyway. **Never ask her for real examples.** Test material is public (ASIC samples) or synthetic only, until a firm pilot provides real files under proper controls.

### Open questions for the domain partner
1. ~~**Couples and joint clients**~~: **answered 9 Oct 2026**. One shared folder, e.g.
   `Black, Brad & Zara` (`client_model.joint_client` in `knowledge_base.json`). Husband's
   first name first, the convention firms expect (13 Oct 2026).
2. ~~**Clients that aren't people**~~: **answered 13 Oct 2026**. The trust, SMSF or company
   is the client. Each one has its own folder under its own name, separate from the people
   behind it (`client_model.entity_client`).
3. ~~**Same name, different people**~~: **answered 13 Oct 2026**. In practice clients share
   only a surname, so `Surname, First name` tells them apart (`client_model.same_surname`).
   Two clients with the *same full name* aren't covered; that goes to the adviser (Q4).
4. ~~**Several names on one document**~~: **answered 13 Oct 2026**. Usually the same surname
   with different first names: file under the surname. If a trustee is named, file under the
   trust. If neither works, flag it and ask the adviser (`client_model.several_names`).
5. ~~**Documents that aren't about one client** (FSG, PDS)~~: **answered**. See "Settled
   domain answers".
6. ~~**Inside a client folder**~~: **answered 9 Oct 2026**. One sub-folder per advice event,
   named after the event; see "Folder levels" above.
7. ~~**Worst mistakes**~~: **answered 13 Oct 2026**. *All* of it needs 100% certainty:
   document type, client name, advice stage and the new document name, because any of them
   being wrong can mean compliance fines and regulator problems
   (`review_policy.certainty_decision`). So a person confirms every document; **nothing is
   filed automatically**, even at 90%+. This replaces the auto-file step in the pipeline above.
8. ~~**Renaming**~~: **answered 13 Oct 2026**. Yes, documents *and folders* are renamed.
   Every rename records the old name, new name, who and when, and users can see who renamed
   it so they can follow up with questions (`filing_model.renaming`; needs the audit log, #7).
9. ~~**Other documents a firm holds**~~ (from #61 / #23): **answered 13 Oct 2026**. Emails,
   letters of outcome from government, invoices, ID documents, tax returns, and provider
   forms. None are document types yet; they go to review until they are.
