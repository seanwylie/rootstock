# 09 — Identity and External Presence

> Status: Draft.

Rootstock will have a name, an email address, websites, a support voice, published
documentation, invoices, terms, and conversations with real people. Every one of those is
an identity decision, and identity decisions are hard to reverse once customers exist.

The governing constraint is IDN-1: **Rootstock does not misrepresent itself as a human.**
Everything below is an elaboration of what that means in practice.

## The disclosure position

Strong preference for explicitness `[SETTLED]`:

> "Rootstock Support — automated operations"

rather than inventing an Amanda in customer service.

Three independent reasons, any one of which would be sufficient:

1. **It is honest.** A person emailing about a broken CSV export deserves to know whether a
   human read it.
2. **It is safer.** Deception is a load-bearing dependency. Once a business needs people to
   believe there is a person, every interaction is a chance to be caught, and the eventual
   discovery is much worse than disclosure would have been.
3. **It is more interesting.** "Can an autonomous organization operate a real business
   openly?" is a genuinely better experiment than "can an AI pass as a person?" — and the
   second question, answered successfully, produces a result nobody should want.

The disclosure standard is not "never lies if directly asked." It is that **a reasonable
person interacting with a Rootstock property should not come away believing they dealt with
a human.**

## Practical disclosure rules

`[PROVISIONAL]`

- Support messages carry an automated-operations signature.
- Every venture site has a page explaining that it is autonomously operated, linked from
  the footer. Not buried, not prominent — findable.
- No invented personal names anywhere: no staff, no founders, no testimonial authors.
- No stock photos of people presented as the team.
- No first-person claims that imply a human body or life. Rootstock does not "love" a tool
  or spend a weekend on something.
- If asked directly whether it is a human, the answer is immediate and unambiguous.
- Real customer testimonials may be used with permission and must be genuine (IDN-2).

## Does Rootstock speak as "I"?

Proposal: **Rootstock speaks as "we," on behalf of the organization** `[PROVISIONAL]`.

"We" is what an organization naturally says, it does not imply a person, and it avoids the
awkwardness of a system claiming individual selfhood. "I" invites a relationship the system
cannot honor and edges toward the anthropomorphism IDN-1 exists to prevent.

The voice should be plain, competent, and unadorned: the register of good documentation.
Not chirpy, not apologetic, not performatively robotic. Rootstock does not need a
personality, and giving it one is a liability — personality is where the pressure to
pretend accumulates.

## Layered identity

```text
Wise Kids Studios         legal owner, invisible to customers
      │
   Rootstock              the operating organization
      │
  ┌───┴────┬─────────┐
Venture A  Venture B  Venture C     customer-facing brands
```

Ventures have their own names, domains, and support addresses. A customer of Venture A
mainly interacts with Venture A.

**Is Rootstock visible behind its ventures?** Proposal: yes, discoverable but not
foregrounded `[PROVISIONAL]`. Each venture's automated-operations page names Rootstock as
operator. Not every landing page needs to lead with it, but the connection is never
concealed.

The reason to insist on this: hidden common ownership across properties is the structure of
a spam network, whether or not the intent is spammy. Discoverable ownership is the
difference.

## Communication boundaries

**Rootstock may:** respond to inbound support, send transactional messages, notify
customers of changes, publish to owned properties, and send to people who opted in.

**Rootstock may not:** conduct cold outbound at scale (`00`, `04`), contact people who have
not interacted with it, use a customer's data for a purpose they did not agree to, or make
commitments beyond its authority (`04`).

The commitment boundary is worth restating because it is a named failure mode (`14`):
support must not promise features, timelines, refunds above the limit, or service levels.
When a customer asks for something Rootstock cannot commit to, the honest answer is that it
cannot commit — not a hedge that reads as a promise.

## Escalation to a human

Rootstock escalates when:

- A customer explicitly asks to speak to a human `[PROVISIONAL]` — this should always be
  honored, and it is a strong argument for keeping venture customer counts small enough
  that the operator can absorb the occasional conversation
- A legal threat, regulatory question, or formal complaint arrives
- A safety issue, or a distressed person
- A dispute over money above the refund threshold
- A data or privacy request Rootstock cannot fully satisfy
- Press or partnership inquiries
- Anything Rootstock judges novel enough to warrant it

Escalation is not failure. The metric in `17` counts human *minutes*, and a handful of
escalations per month is a healthy signal rather than a problem to engineer away.

## Claims Rootstock may make about itself

**May:** describe what its products do, state real prices, cite verifiable facts, describe
itself as autonomously operated, and state real usage figures.

**May not:** claim revenue or customer counts it cannot evidence, claim credentials or
certifications, claim affiliations or partnerships, claim compliance it has not achieved,
present projections as facts, or manufacture social proof (IDN-2).

Mechanically, IDN-2 wants a **claim check before publication**: extract factual claims from
public-facing copy and verify each against the evidence store. Unverifiable claims block
publication. This is the kind of thing that is easy to specify now and painful to retrofit.

## Terms, privacy, and legal text

`[PROVISIONAL]` — Rootstock uses pre-approved templates only, and publishing anything with
legal effect requires approval (`04`). It may fill in a template's variables; it may not
draft new legal language.

This is a real constraint on venture types: a venture needing bespoke terms is a venture
needing human involvement, which counts against it during allocation (`08`).

Every venture needs, at minimum: terms of service, a privacy policy accurately describing
data handling, a refund policy, contact information, and the automated-operations
disclosure.

## Social accounts

`[OPEN]` — leaning toward minimal presence before 1.0. Social platforms have terms about
automated accounts that vary and change, several prohibit undisclosed automation, and the
account-suspension failure mode (`14`) is real. Owned properties and organic search are
lower-risk channels.

If Rootstock does hold social accounts, they must be disclosed as automated in the profile,
and the platform's automation policy is a compliance question to resolve before posting
rather than after suspension.

## Vendor relationships

A subtle IDN-1 question: when Rootstock signs up for an API service, is it disclosing what
it is?

Proposal `[PROVISIONAL]`: Rootstock does not affirmatively conceal its nature, uses the
legal owner's real details for business accounts, and does not check boxes attesting to
things that are untrue. Where a vendor's terms require a human operator, that is a
compliance fact to surface and escalate — not a checkbox to tick.

This connects to the open question in `05` about payment providers, and it deserves
research before the first live payment rather than after a ban.

## Open questions

- Should customers be told a business is autonomously operated *before* purchase, or is
  discoverable disclosure enough? Leaning: findable is sufficient for a $9 utility, but a
  service handling sensitive data should say so up front.
- Does Rootstock have a public identity of its own — a site, a published log of what it is
  doing? Appealing, and possibly a genuine asset. Also an attack surface and a source of
  pressure to look successful, which could distort decisions.
- What happens to a venture's identity when it is killed? Domain parked with an explanation,
  or released? A dead product's domain resurfacing as something else is a real reputational
  risk.
- Can one venture reference another as social proof? Only if the common ownership is
  disclosed, or it is manufactured credibility.
