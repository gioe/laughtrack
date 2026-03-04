# GET /api/v1/shows

Search for comedy shows near a zip code.

## Request

```
GET /api/v1/shows
```

### Headers

| Header | Required | Description |
|--------|----------|-------------|
| `X-Timezone` | No | IANA timezone name used for date filtering (e.g. `America/New_York`). Defaults to `UTC`. |

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `zip` | string | **Yes** | — | 5-digit US zip code for geographic filtering. |
| `distance` | number | No | `25` | Search radius in miles. |
| `from` | string | No | — | Start date in `YYYY-MM-DD` format. Shows on or after this date are returned. |
| `to` | string | No | — | End date in `YYYY-MM-DD` format. Shows on or before this date are returned. |
| `page` | integer | No | `0` | **0-indexed** page number. Page 0 is the first page. |
| `size` | integer | No | server default | Number of results per page. |
| `comedian` | string | No | — | Filter by comedian name or ID. |
| `filters` | string | No | — | Comma-separated filter tag slugs. |

> **Pagination note:** The `page` parameter is 0-indexed — `page=0` returns the first page, `page=1` the second, etc. The internal query engine uses 1-indexed pages; the API translates automatically.

## Validation

| Condition | Status | Error |
|-----------|--------|-------|
| `zip` missing or not 5 digits | `400` | `"zip is required and must be a 5-digit US zip code"` |
| `from` not valid `YYYY-MM-DD` | `400` | `"from must be a valid date in YYYY-MM-DD format"` |
| `to` not valid `YYYY-MM-DD` | `400` | `"to must be a valid date in YYYY-MM-DD format"` |
| Unexpected server error | `500` | `"Failed to fetch shows"` |

## Authentication

This endpoint is publicly accessible without authentication. When a user session is present (via session cookie or equivalent), lineup items will include per-user `isFavorite` state. Without a session, `isFavorite` is always `false`.

## Response

### 200 OK

```json
{
  "total": 42,
  "data": [
    {
      "id": 1001,
      "name": "Friday Night Laughs",
      "date": "2026-03-07T20:00:00.000Z",
      "clubName": "The Comedy Store",
      "address": "8433 Sunset Blvd, West Hollywood, CA 90069",
      "imageUrl": "https://cdn.example.com/venues/the-comedy-store.jpg",
      "tickets": [
        {
          "price": "20.00",
          "purchaseUrl": "https://tickets.example.com/shows/1001",
          "type": "general",
          "soldOut": false
        }
      ],
      "lineup": [
        {
          "id": 42,
          "uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
          "name": "Jane Smith",
          "imageUrl": "https://cdn.example.com/comedians/jane-smith.jpg",
          "isFavorite": false,
          "isAlias": false
        }
      ]
    }
  ],
  "filters": [
    { "id": 3, "name": "Clean", "slug": "clean", "selected": false },
    { "id": 7, "name": "Improv", "slug": "improv", "selected": true }
  ]
}
```

#### Top-level fields

| Field | Type | Description |
|-------|------|-------------|
| `total` | integer | Total number of matching shows (across all pages). |
| `data` | array | Shows for the requested page. |
| `filters` | array | Available filter facets for the result set. |

#### `data[]` — Show object

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Unique show ID. |
| `name` | string \| null | Show title. |
| `date` | ISO 8601 string | Show date/time in UTC. |
| `clubName` | string | Name of the venue. |
| `address` | string | Venue street address. |
| `imageUrl` | string | URL of the venue image (derived from the club name). |
| `tickets` | array | Available ticket options (see below). |
| `lineup` | array | Comedians performing (see below). |

#### `data[].tickets[]` — Ticket object

| Field | Type | Description |
|-------|------|-------------|
| `price` | string \| null | Ticket price as a fixed-2-decimal string (e.g. `"20.00"`), or `null` if unknown. |
| `purchaseUrl` | string | URL to purchase the ticket. |
| `type` | string | Ticket tier or category (e.g. `"general"`, `"VIP"`). |
| `soldOut` | boolean | Whether this ticket type is sold out. |

#### `data[].lineup[]` — Comedian object

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Comedian ID. |
| `uuid` | string | Comedian UUID (use for deep links and stable references). |
| `name` | string | Comedian display name. |
| `imageUrl` | string | URL of the comedian's headshot. |
| `isFavorite` | boolean | Whether the authenticated user has favorited this comedian. Always `false` when unauthenticated. |
| `isAlias` | boolean | Whether this comedian entry is an alias for another comedian. |

#### `filters[]` — Filter object

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Tag ID. |
| `name` | string | Human-readable filter label. |
| `slug` | string | URL-safe slug; pass this value in the `filters` query param to activate the filter. |
| `selected` | boolean | Whether this filter is currently active in the request. |

### 400 Bad Request

```json
{ "error": "zip is required and must be a 5-digit US zip code" }
```

### 500 Internal Server Error

```json
{ "error": "Failed to fetch shows" }
```

## Example Requests

### First page of shows near NYC this weekend

```http
GET /api/v1/shows?zip=10001&from=2026-03-07&to=2026-03-08&page=0&size=20
X-Timezone: America/New_York
```

### Second page, expanded radius

```http
GET /api/v1/shows?zip=90210&distance=50&page=1&size=20
```

### Filter by comedian

```http
GET /api/v1/shows?zip=60601&comedian=John+Doe&page=0
```

### Filter by tag slug

```http
GET /api/v1/shows?zip=10001&filters=clean,improv&page=0
```
