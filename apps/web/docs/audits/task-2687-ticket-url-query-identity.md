# TASK-2687 - Ticket URL Query-String Identity Audit

Ticket URLs where the event identity lives in the query string must keep the
entire URL through user navigation, click analytics, affiliate routing, and
admin reporting. The audited examples are:

- ThunderTix: `https://theannoyance.thundertix.com/orders/new?performance_id=314159`
- Chanhassen: `https://tickets.chanhassendt.com/Online/default.asp?BOparam::WScontent::loadArticle::permalink=stevierays`
- Flappers: `https://www.flapperscomedy.com/site/shows.php?shid=123456`

## Findings

- UI navigation uses `buildTicketOutboundHref()` to put the full destination in
  the `url` query parameter on `/api/v1/tickets/out`. `URLSearchParams` encodes
  the nested query string, and `/api/v1/tickets/out` retrieves it with
  `searchParams.get("url")`, so the nested `?` and `&` survive.
- Affiliate routing parses the destination with `new URL(destinationUrl)` and
  returns `parsed.toString()`. Direct venue URLs have no affiliate rule, so the
  routed URL is the original full URL. Affiliate insertion for supported
  providers mutates `searchParams`, which appends the affiliate parameter without
  discarding existing query parameters.
- Outbound click analytics stores both `destination_url` and
  `routed_destination_url` in `ticket_purchase_click_events`. Those columns store
  full URLs, including query strings.
- The client-side `/api/v1/ticket-clicks` beacon path also validates with
  `new URL(value).toString()` and stores the full `destination_url`. Current web
  CTA links route through `/api/v1/tickets/out`, so this path is fallback
  analytics rather than the primary navigation path.
- Admin aggregate reporting for `/api/v1/ticket-clicks` reports totals filtered
  by date/show/club. It intentionally does not group by destination URL, host, or
  path, so it does not collapse query-string event identity. Raw event rows keep
  the full destination for any later URL-level analysis.

## Regression Coverage

The web test suite now pins the three query-identity URL shapes through:

- outbound href construction
- affiliate/direct routing
- outbound redirect response and persisted click metadata

No production code change was needed for this audit.
