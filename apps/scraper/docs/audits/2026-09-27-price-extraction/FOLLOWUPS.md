# Price audit repair tasks — TASK-4056

The existing backlog was checked semantically and all proposed titles passed duplicate checks. All16 imports succeeded after dry run; stored scopes and two criteria per task were verified. The test commands are implementation contracts, not existing tests that passed during this investigation.

| Task | Deliverable | Evidence context |
| --- | --- | --- |
| TASK-4089 | Preserve Squarespace ticket product variant prices | 713 |
| TASK-4090 | Recognize explicitly free admission on dated Squarespace event details | 714 |
| TASK-4091 | Retain Second City ticket allocation prices and availability | 715 |
| TASK-4092 | Recover UCB physical admission prices from event details | 716 |
| TASK-4093 | Retain SeeTickets calendar price ranges by event identity | 717 |
| TASK-4094 | Enrich TNEW performances with verified admission offers | 718 |
| TASK-4095 | Recover Ticket Tailor detail offers without losing package semantics | 719 |
| TASK-4096 | Associate Odoo registration offers with their event | 720 |
| TASK-4097 | Add currency-safe Showpass detail price enrichment | 721 |
| TASK-4098 | Recover Comix admission prices from linked checkout offers | 722 |
| TASK-4099 | Retain McCurdys venue-published ticket prices | 723 |
| TASK-4100 | Extract verified Zanies admission prices instead of placeholder zeros | 724 |
| TASK-4101 | Enrich Flop House tickets from matched Eventbrite offers | 725 |
| TASK-4102 | Recover Denver Comedy Lounge prices from streamed event data | 726 |
| TASK-4103 | Exclude Que Sera post-show happy hours from comedy inventory | 727 |
| TASK-4104 | Exclude Standing Room Only season-pass products from shows | 728 |

TASK-4086 was extended with criterion13349 and context712 for131 verified Grisly Pear price examples. It already owns calendar/detail identity recovery, so a second Grisly implementation task would duplicate work.

created-tasks.json records exact scopes, descriptions and verification contracts. Sources are retained under parent/, platforms/, ticketing/ and venues/. Context entries point directly at real positive and negative fixtures. Every implementation must recheck current identity and sale availability before production writes; snapshot counts are evidence, not future acceptance targets.

No hard dependencies were added. Each parser/enrichment task has independent real-source verification. Squarespace product and semantic-free tasks share a module but neither requires the other to land. TASK-4065 (Second City room/date identity) and TASK-4080 (Port collisions) remain relevant to safe production matching; parser work can proceed while unresolved performances remain excluded. TASK-4097 must preserve unknown for unsupported currency rather than assuming a global schema/UI currency rollout is authorized.

TASK-4103 and TASK-4104 address non-show products, not prices. Cleanup criteria require dependent-data checks and protected genuine-performance controls.
