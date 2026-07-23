# Discovery Ranking Contract

## Status and scope

This document defines the product and measurement contract for ranking Laughtrack
recommendations. The first implementation target is the web **Near You** show
surface. Other surfaces may reuse the feature definitions, but each surface must
choose and evaluate its own ranking policy.

This is a contract for later implementation work. It does not rename existing
database columns, change the current popularity formulas, or authorize a rollout.

## Product decision

The objective is **discovery**: help a person find an appealing, relevant live
comedy option they can act on.

Discovery is not synonymous with recognition. Recognition can help with cold
starts and confidence, but it must not dominate ranking. Recent demand is evidence
of momentum; change in demand is evidence of growth. Neither raw demand nor an
existing popularity value is the final ranking objective.

The ranking system must preserve these boundaries:

1. Eligibility and availability are evaluated before ranking.
2. Prominence, momentum, growth, affinity, availability, and confidence remain
   separate, inspectable features.
3. A discovery rank is specific to a surface and ranking-policy version. It is
   not persisted as a universal entity score.
4. Behavioral demand is normalized by exposure. More impressions alone must not
   be interpreted as growth.
5. Exploration is deliberate, measurable, and stable for a user session. It is
   not untracked randomness.
6. Missing evidence lowers confidence; it does not prove low quality or low
   relevance.

## Vocabulary

### Prominence

Prominence is durable recognition or established reach. It changes slowly and is
global rather than user-specific.

Examples include established social reach, a sustained performance history, and
other corroborated identity signals. The existing comedian, club, and show
`popularity` columns are legacy composite measures. They may be used as
prominence inputs during migration, but their values must not be presented as a
discovery score or used as the sole ranking policy.

Prominence has three permitted roles:

- a small prior when stronger contextual evidence is absent;
- a tie-breaker after contextual and growth signals; and
- an identity or data-confidence input in ingestion workflows.

In a weighted candidate policy, prominence may contribute no more than 10% of the
normalized ranking score. It may contribute zero. Raising that ceiling requires a
new policy version and a recorded product decision.

### Demand

Demand is an observation, not a rank. It describes demonstrated interest during
a defined period.

Examples include unique ticket-intent actors, detail engagement, new favorites,
and reliable sold-out evidence. Raw counts are not comparable across entities
with different exposure. Behavioral demand must therefore retain its surface,
experiment variant, item rank, actor, and impression attribution when those are
available.

Sold-out evidence is positive demand evidence but negative availability evidence.
The same fact may contribute to demand history while excluding an item from an
actionable recommendation surface.

### Momentum

Momentum is the current level of recent, exposure-normalized demand and relevant
supply activity. It answers: **is this attracting meaningful attention now?**

For behavioral signals, the default recent window is the trailing 7 complete
days. Rates use qualified impressions or unique exposed actors as the denominator,
not total application traffic. When the 7-day window lacks the minimum evidence
defined by the ranking policy, the feature falls back to a trailing 28-day window
and reports lower confidence.

Supply activity may include upcoming distinct engagements, but repeated showtimes
for one engagement must not masquerade as independent momentum.

### Growth

Growth is a change in a comparable rate relative to the entity's own baseline. It
answers: **is meaningful attention or opportunity increasing?**

The default behavioral comparison is:

- recent period: trailing 7 complete days;
- baseline period: the preceding 28 complete days; and
- comparison unit: a per-day or per-qualified-impression rate, as appropriate.

Social signals refresh more slowly. Their default comparison uses the latest
valid observation in the trailing 28 days against the latest valid observation
in the preceding 28 days. A single observation has unknown growth, not zero
growth.

Growth calculations must:

- distinguish a zero baseline from a missing baseline;
- use smoothing or minimum denominators so tiny samples cannot dominate;
- cap extreme values before combining signals;
- carry the underlying observation count and confidence; and
- remain reproducible for a fixed `asOf` time.

Demand is therefore an input to growth, but demand level and demand growth remain
separate features.

### Affinity

Affinity is the estimated fit between an item and the current user or session.
It is contextual and evaluated at request time.

Explicit preferences, favorites, selected location, chosen filters, and current
query intent are valid inputs. Behavioral personalization must not be introduced
without a documented consent and retention model. When no affinity evidence is
available, the feature is neutral; it must not penalize anonymous or new users.

### Availability

Availability represents whether the user can act on a recommendation now. It is
evaluated at request time and has three states:

- **available**: future inventory has at least one known, non-sold-out purchase
  path;
- **unknown**: the show is not known to be sold out, but inventory reliability or
  a purchase path is incomplete; and
- **unavailable**: the show is in the past or reliable evidence says the show is
  sold out or otherwise not purchasable.

For the Near You pilot, unavailable shows are ineligible. Unknown shows may remain
eligible so incomplete upstream ticket data does not erase legitimate events, but
they receive no availability advantage. The existing shared available-show filter
is the minimum eligibility rule until a richer inventory state ships.

### Confidence

Confidence describes the amount, freshness, and reliability of evidence behind a
feature. It is not popularity and must not independently improve rank.

Confidence can dampen momentum or growth toward a neutral value. It must expose
why it is low: insufficient impressions, missing baseline, stale observation,
unreliable inventory, or incomplete attribution. Evidence becomes stale after two
expected refresh intervals unless a signal-specific contract says otherwise.

### Exploration

Exploration reserves exposure for eligible items whose relevance is plausible but
whose evidence is sparse. It reduces incumbent feedback loops and creates the
observations needed to learn about new or local acts.

The Near You candidate starts with a configurable 10% exploration allocation.
Assignment must be stable for the same actor and experiment period, respect all
eligibility rules, and be identifiable in impression events. Exploration items
must still satisfy geography, date, visibility, and availability constraints.

## Feature time semantics

| Feature | Evaluation time | Default window | Missing-data behavior |
|---|---|---|---|
| Prominence | Latest trusted refresh | Slow-moving; no short-term boost | Neutral prior with reduced confidence |
| Momentum | Ranking `asOf` time | 7 days; fall back to 28 days when sparse | Neutral with reduced confidence |
| Behavioral growth | Ranking `asOf` time | 7 recent days vs preceding 28 days | Unknown growth |
| Social growth | Latest valid snapshots | Latest in 28 days vs latest in preceding 28 days | Unknown growth |
| Affinity | Request time | Current explicit context; optional recency-decayed history | Neutral |
| Availability | Request time | Current future inventory | Unknown state, never inferred sold out |
| Confidence | Same `asOf` as its feature | Signal-specific freshness and sample floor | Explicit low-confidence reason |
| Exploration | Experiment assignment time | Stable for session or configured experiment period | No exploration identity means control behavior |

Every persisted feature snapshot must include its `asOf` time, policy or feature
version, source windows, confidence, and sufficient counts to explain the value.

## Ranking pipeline

Every discovery surface follows the same stages even when it chooses different
features or weights.

### 1. Generate eligible candidates

Apply hard product constraints before scoring: entity visibility, canonical
identity, location/radius, requested dates, and availability. A high score cannot
rescue an ineligible item.

### 2. Compute independent features

Compute the features above without folding one feature into another. In
particular, confidence dampens a feature and availability controls actionability;
neither is an unlabelled popularity bonus.

### 3. Rank for the surface

The policy combines contextual relevance, momentum, growth, affinity when known,
and a bounded prominence prior. Feature values and weights must be versioned and
logged with the experiment assignment. Final weights are calibrated only after
the feature-distribution task has real observations; this contract intentionally
does not invent weights from current popularity distributions.

The following constraints apply to every Near You candidate policy:

- geography and requested date constraints are never relaxed by score;
- unavailable inventory is not promoted as an actionable recommendation;
- confidence prevents sparse growth from overwhelming well-supported evidence;
- prominence contributes at most 10%; and
- an explicit exploration allocation is applied after eligibility.

### 4. Present and measure

An impression is qualified only when the item is actually presented in the
viewport for the measurement duration defined by the event contract. Returning an
item from the server is not an impression. Detail and ticket-intent events retain
the originating surface, policy version, experiment variant, item rank, and
impression identifier when available.

## Near You pilot

### Control

The control is the web Near You behavior at the start of the experiment:

1. filter to future shows at visible clubs inside the resolved ZIP radius;
2. apply the shared available-show predicate;
3. fetch up to 50 candidates ordered by stored show popularity and date;
4. order those candidates by show popularity, lineup popularity, distance, date,
   and stable ID; and
5. return the first eight.

The implementation must snapshot the precise control policy under a version name
before starting the experiment. Later unrelated changes must not silently mutate
the control arm.

### Candidate

The candidate uses the same hard geography, date, visibility, and minimum
availability universe as the control. It replaces popularity-first ordering with
the versioned discovery pipeline defined above. Missing feature data falls back to
neutral values and lower confidence rather than excluding the show.

Experiment assignment is 50/50 by stable profile ID or anonymous visitor ID. An
actor remains in one variant for the experiment. Bots, internal test traffic, and
events without a valid qualified impression are excluded from outcome analysis.

### Primary outcome

The primary outcome is **unique ticket-intent actors per unique qualified Near You
impression actor**, measured by variant during the attribution window. Repeated
clicks by one actor on the same show count once. Ticket intent is used until
confirmed purchase conversion is available.

### Secondary outcomes

- show-detail actors per qualified impression actor;
- distinct shows receiving meaningful engagement;
- new favorites attributable to Near You, once favorite timestamps exist;
- actionable-inventory engagement; and
- exploration-item engagement and subsequent confidence gain.

### Guardrails

The candidate must satisfy all of these guardrails:

- every result remains inside the actor's configured geography and date scope;
- the share of impressions on actionable inventory does not fall by more than 2
  percentage points;
- p95 Near You response latency does not regress by more than 100 ms or 10%,
  whichever allowance is larger;
- API and client measurement errors remain below 1% of attempted event batches;
- the share of exposure received by the top prominence decile does not increase
  by more than 5 percentage points;
- lower-prominence and new eligible items do not receive less aggregate exposure
  than in control; and
- missing features do not remove otherwise eligible shows.

Metrics must also be segmented by anonymous/authenticated actor, geography,
availability state, confidence band, and exploration/control allocation. Aggregate
improvement must not conceal a material regression in a major segment.

### Observation and decision thresholds

Do not make a ship decision before both variants have:

- at least 14 complete days of observation;
- at least 1,000 qualified impression actors each; and
- at least 50 unique ticket-intent actors each.

If those floors are not reached after 14 days, continue to 28 days. After 28 days,
record the result as inconclusive rather than relaxing the sample requirements.

Ship the candidate only when:

- ticket intent shows at least a 5% relative lift over control;
- the 95% confidence interval for relative lift has a lower bound above -2%; and
- every guardrail passes.

Tune and rerun when the result is inconclusive, the practical lift is below 5%, or
a non-critical guardrail misses. Do not combine multiple candidate policy versions
into one analysis window.

### Rollback rules

The feature flag must restore the control immediately. Roll back before the normal
decision window when any of these occurs:

- a privacy, authorization, or cross-actor attribution defect;
- an availability or geography eligibility violation;
- a sustained error rate above 1% for 30 minutes;
- a sustained p95 latency regression above 250 ms for 30 minutes; or
- after the first 500 qualified impression actors per variant, a ticket-intent
  relative-lift confidence interval whose upper bound is below -5%.

After rollback, retain the variant and policy-version labels in historical events,
record the reason, and require a new policy version before another pilot.

## Known current limitations

The pilot requires measurement and ranking work that the current system does not
yet provide:

- Near You retrieves only the first 50 popularity-ordered database candidates
  before applying distance and lineup tie-breakers. A show outside that pool
  cannot be discovered by request-time reranking.
- Existing click signals are raw counts rather than rates normalized by qualified
  impressions, so they cannot establish growth and can reinforce prior exposure.
- Existing popularity composites mix recognition, current activity, and demand
  proxies. They cannot be relabeled as prominence or growth without decomposing
  and validating their inputs.
- Sold-out evidence currently affects both popularity and eligibility. The pilot
  must preserve the historical demand observation separately from the current
  actionable-inventory state.
- Product labels such as **Trending** currently do not guarantee measured velocity.
  They must not be used for the candidate until the growth contract is implemented.
- The current event model does not yet guarantee viewport-qualified impressions,
  stable experiment attribution, or all counts needed for the decision thresholds.

These are prerequisites for implementation tasks, not reasons to weaken the
definitions or experiment thresholds in this contract.

## Reference implementation locations

Implementers should validate the current behavior at these entry points before
changing it:

- `apps/web/lib/data/home/getShowsNearZip.ts` for database candidate generation;
- `apps/web/lib/data/home/findShowsForHome.ts` for Near You reranking and result
  limits;
- `apps/web/lib/data/show/showSelect.ts` for the shared `AVAILABLE_SHOW_WHERE`
  minimum inventory predicate; and
- `apps/scraper/src/laughtrack/foundation/utilities/popularity/scorer.py` and
  `apps/web/lib/popularity/comedianPopularity.ts` for legacy feature composition.

Paths may move, but the versioned control must preserve the behavior described in
this document rather than relying on an unversioned helper name.

## Existing popularity compatibility

This contract does not require an immediate schema rename. Existing popularity
fields can continue to support backward-compatible sorts, administrative views,
ingestion confidence gates, and current clients while the pilot is developed.

New discovery code must name the role when consuming an existing popularity value:
`prominence`, `legacyPopularity`, or another explicit adapter name. It must not pass
an unexplained `popularity` value directly into the final discovery rank.

User-facing copy should prefer concrete language such as **Near You**, **On the
Rise**, **Active**, or **Popular** only when the underlying policy matches that
claim. **Trending** requires measured recent change, not a static threshold or
shuffle.

## Versioning and ownership

Every ranking policy and feature-definition change receives a new version. Stored
events and snapshots retain that version so historical comparisons remain valid.
Changing a time window, normalization rule, confidence floor, prominence ceiling,
exploration allocation, or eligibility rule is a versioned behavior change.

The product owner is the final ship/tune/rollback decision-maker. Implementation
owners are responsible for data correctness, reproducibility, privacy, and
operational visibility. A ranking policy is not considered launched until its
monitoring can produce the primary outcome and every guardrail without ad hoc SQL.

## Out of scope for the first pilot

- renaming or deleting existing popularity columns;
- changing scraper identity or comedy-classification gates;
- machine-learned ranking;
- cross-surface or mobile rollout;
- behavioral personalization beyond the documented affinity inputs;
- exposing numeric ranks, scores, or popularity tiers to users; and
- treating ticket intent as a confirmed purchase.
