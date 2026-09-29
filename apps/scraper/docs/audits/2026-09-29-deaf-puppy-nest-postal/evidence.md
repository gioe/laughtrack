# TASK-4071: address-specific postal evidence

Reviewed 2026-09-29. Both visible active US venues have valid business coordinates,
but missing structured ZIPs exclude them from ZIP-based nearby discovery. Actual
production club searches with name filters, a5-mile radius and includeEmpty=true
returned zero for551 at95336 and8713 at43202. before/nearby-before files reproduce
this, without using the ZIP inside the database address as independent evidence.

| Club | Decision | Independent address-specific evidence |
|---|---|---|
|551 Deaf Puppy Comedy Club|Fill blank ZIP with95336|City of Manteca CEQA permit notice2026040414, April9 2026, identifies the club and project location125/127 N Main St, Manteca CA95336. Venue site confirms127 N.Main St and city. Live Google business place ChIJ56C9BrpBkIARwR05O3V4F3M matches name,website,address and95336.|
|8713 The Nest Theatre|Fill null ZIP with43202|Columbus City Council September27 2021 minutes, page2, permit16534310010 names Columbus Improv Theatre LLC DBA The Nest Theatre at2643 N High St, Columbus OH43202. Current Google place ChIJe4VjWzaPOIgRjuXnR1D1PQA matches business,website,street and43202.|

Primary documents:
- https://ceqanet.lci.ca.gov/2026040414
- https://columbus.legistar.com/View.ashx?GUID=1CA8CD78-1E97-445A-B7E8-2A3CB869A336&ID=895037&M=M

Deaf Puppy's government notice includes adjoining125 and127 under an expansion;
retain the venue's127 street and existing business map point(37.7980935,-121.2168019).
Nest retains2643 N High and(40.016155999999995,-83.0122253). Its government record is
historical; current independent business details confirm the same address. No
physical relocation or source-ownership change is being inferred.

## Conflicting or unavailable evidence

- Deaf Puppy https://www.deafpuppyclub.com/ and JSON-LD omit ZIP; not sufficient alone.
- https://columbuscomedyfest.com/services/the-nest-theatre/ lists43215 while its
  2025 event page https://columbuscomedyfest.com/event/stand-up-improv-showcase-nest-2025-thursday-02/
  lists43202 for the same street. Captured both live pages. Prefer the government
  business/address record over conflicting partner metadata.
- TASK-4044's September24 attempts could not read nesttheatre.com with ordinary or
  scraper-browser reads. That limitation is not evidence of a wrong ZIP or source
  outage: the configured ingestion source is a separate VBO Tickets plugin.
- An indexed Ohio2025Q1 liquor report also names Nest at43202, but its2477-page PDF
  page was not located reproducibly. It is not required for this decision.
- Web PDF screenshot returned cache-miss; direct council PDF text and download
  succeeded. nest-permit.json preserves the exact identifying record and page.

## Inventory and repair boundary

Deaf Puppy:207 historical shows,62 upcoming;214 tickets,118 lineup links,282tags,
one saved show,138scraper-run links. SeatEngine source594 / venue531 stays unchanged.
Nest:108 historical shows,36 upcoming;108tickets,5lineup links,303tags,118run links.
VBO source5863 and Live Shows category remain unchanged. Snapshots capture all
club/show foreign-key counts and full-row fingerprints, including home-comedian
and click links. No show, lineup, ticket, source, address, map point, website,
timezone, visibility or existing valid postal field is edited.

Only new migration and audit artifacts are required. QueryHelper.getZipCodeClause,
findClubsWithCount and getClubsByZip use structured ZIP membership; coordinates do
not substitute for missing ZIP. Existing SeatEngine/discovery upserts preserve
nonempty ZIPs; VBO updates shows, not club postal metadata.
