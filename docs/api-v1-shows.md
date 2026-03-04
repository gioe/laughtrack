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
| `filters` | string | No | — | Comma-separated filter tags. |

> **Pagination note:** The `page` parameter is 0-indexed — `page=0` returns the first page, `page=1` the second, etc. The internal query engine uses 1-indexed pages; the API translates automatically.

## Validation

| Condition | Status | Error |
|-----------|--------|-------|
| `zip` missing or not 5 digits | `400` | `"zip is required and must be a 5-digit US zip code"` |
| `from` not valid `YYYY-MM-DD` | `400` | `"from must be a valid date in YYYY-MM-DD format"` |
| `to` not valid `YYYY-MM-DD` | `400` | `"to must be a valid date in YYYY-MM-DD format"` |
| Unexpected server error | `500` | `"Failed to fetch shows"` |

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
      "imageUrl": "https://cdn.example.com/shows/1001.jpg",
      "description": "An evening of stand-up comedy.",
      "soldOut": false,
      "tickets": [
        {
          "price": 20,
          "url": "https://tickets.example.com/shows/1001"
        }
      ],
      "lineup": [
        {
          "id": 42,
          "name": "Jane Smith",
          "imageUrl": "https://cdn.example.com/comedians/42.jpg"
        }
      ],
      "tags": [3, 7]
    }
  ],
  "filters": {
    "tags": [
      { "id": 3, "name": "Clean" },
      { "id": 7, "name": "Improv" }
    ]
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `total` | integer | Total number of matching shows (across all pages). |
| `data` | array | Shows for the requested page. |
| `data[].id` | integer | Unique show ID. |
| `data[].name` | string \| null | Show title. |
| `data[].date` | ISO 8601 string | Show date/time in UTC. |
| `data[].clubName` | string | Name of the venue. |
| `data[].address` | string | Venue street address. |
| `data[].imageUrl` | string | URL of the show/venue image. |
| `data[].description` | string | Show description (may be absent). |
| `data[].soldOut` | boolean | Whether the show is sold out. |
| `data[].tickets` | array | Available ticket options. |
| `data[].lineup` | array | Comedians performing. |
| `data[].tags` | integer[] | Tag IDs associated with the show. |
| `filters` | object | Available filter facets for the result set. |

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
