# TASK-4058: reviewed social identities

Reviewed 2026-09-27. Scope: seven unlinked Instagram collisions and four originally visible children of hidden parents. This is an evidence-based data repair, not a rule that equal handles prove identity. `baseline.json` and `queries.json` retain the current record state and lineup provenance. Five pairs support direct alias links; one handle attribution is incorrect; one pair remains unresolved. Three aliases still bypass existing parent suppression; the fourth was already suppressed by TASK-4043.

## Per-record decisions

| ID | Record | Decision | Rationale / paired record |
| --- | --- | --- | --- |
| 162399 | Aiden Bishop | Relink to 180157; retain visible | Aiden/Aidan spelling variant supported by festival and venue biographies. |
| 180157 | Aidan Bishop | Retain canonical | Primary venue uses Aidan; same International Comedy Club/Dublin and international festival career. |
| 166992 | Joyelle Johnson | Relink to 712; retain visible | Short/full professional name; both records already point to the same JoCo Cruise biography. |
| 712 | Joyelle Nicole Johnson | Retain canonical | Official full name and @joyellenicole. |
| 207621 | Jenny Saldana | Relink to 14618; retain visible | Primary guest page uses both accented/unaccented names and @LittleBrownGirlShow. |
| 14618 | Jenny Saldaña | Retain canonical | Preserve accented name and existing official website. |
| 1488180 | Marcus Wiley | Relink to 226475; retain visible | Booking biography uses Marcus Wiley and Marcus D. Wiley for the same performer. |
| 226475 | Marcus D. Wiley | Retain canonical | Official name/site and matching career. |
| 171846 | Zack McGovern | Relink to 908; retain visible | NY comedy venues use both spellings; this row's Stand/West Side lineups support that provenance. |
| 908 | Zach McGovern | Retain canonical | Current NYCC and Stand profiles use Zach. |
| 165737 | Sarah Hennessey | Retain separately; unresolved | No lineup, website, home city, or favorites establishes this row's provenance. BCC uses Sarah/@sarahennessey, but a distinct Pennsylvania improviser also uses Sarah. Do not merge solely on handle or spelling. |
| 735 | Sara Hennessey | Retain separately | Official Sara Hennessey website links @sarahennessey; ownership here is supported. |
| 746 | Julie Lim | Correct handle attribution | Clear @justnesh, 247,000 followers and freshness; archive/remove the corresponding Instagram observation. Keep name, UUID, visibility and distinct identity. No guessed replacement handle or Julie Kim rename. |
| 54369 | Just Nesh | Retain unchanged | Venue biography identifies Taneshia “Just Nesh” Rice and @JustNesh. No reliable evidence makes Julie Lim her alias. |
| 440843 | Cory and Chad - The Smash Brothers | Suppress child | Venue identifies the same twin act as parent; honor existing parent suppression. |
| 223894 | Cory and Chad | Retain hidden parent | Preserve explicit manual block and lineage. |
| 535810 | Jane Don't Does America | Suppress child | Official venue identifies a Jane Don't tour/show, not a separate performer. |
| 549605 | Jane Don't | Retain hidden parent | Preserve explicit manual block and lineage. |
| 1068549 | Therapy Gecko Live | Suppress child | Official venue describes Therapy Gecko's live tour. |
| 312265 | Therapy Gecko | Retain hidden parent | Preserve existing manual_removal decision. |
| 444574 | Mojo Brookzz: I Know You F*ckin' Lying Tour | Retain already hidden child | TASK-4043 has already suppressed this decorated tour title. |
| 235139 | Mojo Brookzz | Retain hidden parent | Official site/venue establish performer/tour relation; preserve existing manual block. |

Some blocked parents are described as comedians by their official sources. This audit does **not** independently endorse the old “not a comic” classification. It preserves explicit moderation decisions while preventing their aliases from circumventing them; any change to parent eligibility needs a separate moderation decision.

## Identity evidence

Sources were inspected on 2026-09-27; summaries are paraphrases. A shared social field or synchronized follower refresh is corroboration, not independent proof.

- **Aidan/Aiden:** [Greenwich Village Comedy Club](https://www.greenwichvillagecomedyclub.com/comedians/aidan-bishop/) describes Aidan's NYC/Dublin career and International Comedy Club residency; the [Irish Film Institute](https://ifi.ie/film/moscow-irish-film-festival-3/) names Aiden as a visiting comedian; [Amnesty's Edinburgh event](https://www.amnesty.org.uk/knowledge-hub/all-resources/critics-victorious-comics-vs-critics-football-match-edinburgh-festival/) also uses Aiden. [Chortle's career account](https://www.chortle.co.uk/features/2013/07/11/18266/bishop_in_china) connects the Aiden spelling to Des Bishop and the same Dublin club.
- **Joyelle:** [Official website](https://joyellenicole.com/), [JoCo Cruise biography](https://jococruise.com/joyelle-nicole-johnson/), and [Earwolf's Joyelle Johnson profile](https://www.earwolf.com/person/joyelle-johnson/) connect the short and full names through matching standup/television credits; both database rows already share the JoCo biography URL.
- **Jenny:** [Our MBC Life guest page](https://ourmbclife.squarespace.com/episodes/laughter-as-medicine) uses both spellings for one guest and supplies @LittleBrownGirlShow; [The Stand](https://thestandnyc.com/comedians/jenny-saldana) corroborates the performer.
- **Marcus:** [Clean Comedy Clinic](https://cleancomedyclinic.com/dr_marcus_wiley.php) uses Marcus Wiley as heading and Marcus D. Wiley in the biography; [official website](https://marcusdwiley.com/) corroborates the Texas Southern/clean-comedy career.
- **Zach/Zack:** [The Stand's Zach profile](https://thestandnyc.com/comedians/zach-mcgovern), [Zack profile](https://thestandnyc.com/comedians/zack-mcgovern), [NYCC current profile](https://newyorkcomedyclub.com/comedians/zach-mcgovern), and [NYCC's archived Ry Daddy Show](https://newyorkcomedyclub.com/events/the-ry-daddy-show) use both spellings in the same venue circuit. The archived event is from 2014; current sidebar dates are not its performance date. Local Zack lineups include The Stand and West Side Comedy Club, including an upcoming West Side appearance.
- **Sara/Sarah:** [Sara's official website](https://www.sarahennessey.com/) supports Sara's handle. [BCC's November 2024 bill](https://www.brooklyncc.com/show-schedule/apocahahalypse-11-23) uses Sarah with that handle, but [Better Than Bacon](https://www.betterthanbaconimprov.com/about) also has a distinct Sarah Hennessey. The unproven database row cannot safely be assigned to either from current provenance.
- **Just Nesh/Julie:** [Improv's performer biography](https://improv.com/hollywood/comic/just%20nesh/) identifies Taneshia Rice as Just Nesh and names @JustNesh; [official website](https://justnesh.com/) corroborates the stage name. Julie's identical 247,000 count derives from that unsupported handle assignment. No reliable source establishes Julie as an alias or supplies a replacement handle.
- **Cory/Chad:** [House of Blues](https://www.houseofblues.com/lasvegas/EventDetail?offerid=86152&tmeventid=0) identifies Cory and Chad as the Smash Brothers twin comedy act.
- **Jane Don't:** [City Winery event](https://tickets.citywinery.com/event/flipphone-presents-jane-dont-does-america-2o8hj2) bills Jane Don't Does America as a show by Jane Don't.
- **Therapy Gecko:** [Arts at the Armory](https://artsatthearmory.org/events/therapy-gecko-live/) identifies Therapy Gecko Live as Therapy Gecko/Lyle's 2026 live tour.
- **Mojo:** [Official website](https://www.mojobrookzz.com/) and [Dominion Energy Center](https://www.dominionenergycenter.com/events/detail/mojo-brookzz) connect Mojo Brookzz with the decorated tour title.

## Repair contract and verification

Migration: `20260927150000_repair_reviewed_social_identities`.

All five aliases link directly to existing visible roots. UUIDs, lineup items, favorite seeds, podcast links and episode appearances are retained. No identities are deleted or renamed. Julie has zero lineup/favorite/accepted-podcast/accepted-appearance signals and no other follower counts, so her popularity becomes zero with the incorrect Instagram input removed. No image assets establish Julie's legacy image provenance; that image flag is left unchanged.

The migration locks and checks exact expected identity states. Nine before/after records and the one removed follower observation are archived without cascading foreign keys. Replay accepts only the recorded post-state and never overwrites the original archive. A commented rollback checks post-state before restoring values and the exact observation; it refuses later conflicting changes. UTC is explicit for timestamp comparisons.

`validation.json` records PostgreSQL checks against temporary copies of production-shaped tables, enclosed in an outer rollback: intended changes only, preservation of every copied dependent row, replay, stale-state rejection, changed-parent rejection, changed-observation rejection, guarded rollback, and exact restoration. There are no current favorite rows in the 22-record cohort, so existing canonical-resolution, favorites and lineup tests cover nonempty favorite behavior.

Application semantics checked: `resolveCanonicalComedianIdentity` resolves the visible seed to a visible root and aggregates the full family; lineup presentation substitutes a visible direct parent; hidden roots are rejected. Legitimate linked aliases stay visible so their existing UUID favorite seeds and future ingestion remain usable. Suppressed children stay linked to their existing hidden parents.

See `production.json` for post-deployment invariants and `test-results.txt` for the focused application tests. The remaining unresolved handle collision is retained explicitly, not silently reported as fixed.
