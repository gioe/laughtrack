These responses were captured from TicketSource's published
`/ticketshop/web/promoter-list-detailed_ajax.php` POST endpoint on 2026-10-01,
using promoterid=KEGG, localtimeoffset=-360, eventrefno='', and the filename's
startat offset. The published promoter-list-detailed.min.js specifies this request.

Offsets 1, 13, 25, 37 and 49 contain 59 upcoming Comedy Clubhouse performances.
Offset 49 is the last inventory page and has eof=true with eleven events.
A separate request at offset 61 returned HTTP 200 with exactly {"eof":true}:
this captures the endpoint's terminal empty envelope. It does not establish
that the venue's entire live calendar was empty. The empty-calendar regression
reuses this observed envelope at the initial request to test that future state.
