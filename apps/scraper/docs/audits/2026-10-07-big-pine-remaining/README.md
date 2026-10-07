# TASK-4132 — Remaining Big Pine inventory

Status: native evidence reviewed; guarded cleanup and recovery validation pending.

On October 7, 2026, the scraper's SeatEngine client fetched all 53 stored native
show details successfully and the current venue553 feed (16 entries).
The native list and detail responses are in native.json; inventory.json contains
only public show identity fields. Decisions for every remaining row appear in
decisions.json. Private database and dependent-row snapshots stay outside Git.

The reviewed disposition is **36 remove, 16 retain, 1 hold**:

| Product evidence | Remove count |
| --- | ---: |
| Submission inventory, including digital submission7773673/native390223 | 6 |
| Digital Download inventory | 14 |
| Digital/EPK/social-media review service inventory | 7 |
| Virtual Consultation inventory | 5 |
| Camp passes explicitly admitting workshops/panels | 3 |
| Networking game with revival-life add-on | 1 |

Each removal matches a native show ID, venue553, URL, and UTC start instant.
Classification uses explicit inventory/add-on evidence, not broad title words.
For example, submission390223 sells Digital Submission inventory and a written
video/bio-review add-on. Networking game340141 sells a revival life that restores
an eliminated player to competition. These are not performance tickets.

The 16 retained rows have matching native identities and dates and performance
or festival-admission inventory. This includes the Big Pine festival pass363358,
Big Tomato festival361183, and all reviewed named comedy performances. Festival
visibility, source360, platform sources3126/7146 and source targets1/2 must remain
unchanged. This task does not convert the festival into a producer or change the
existing title exclusions.

**Hold522192/native356284:** the database date is May10 at16:00Z, whereas the
fresh native date is May3 at16:00Z. Its workshop/panel inventory confirms an
education product, but the occurrence-date discrepancy remains unresolved.
The cleanup excludes this row and preserves it unchanged; no deletion or date
repair is inferred from its title or from unavailable historical pages.

The original TASK-4111 19-ID deletion list remains frozen. Its old private backup
is not a current before-image and must not be restored over newer writes.

Native endpoints, verified against the client implementation:

- https://services.seatengine.com/api/v1/venues/553/shows
- https://services.seatengine.com/api/v1/venues/553/shows/390223 (submission example)

The new cleanup will use fresh locked snapshots, exact row counts/hashes, private
backups before mutation, and seven-table dependency checks. Deleted show
references on purchase-click records must become null while the records survive.
Recovery must restore shows before cascading dependencies and reattach existing
click rows only after verifying the complete after-image and current schema.
