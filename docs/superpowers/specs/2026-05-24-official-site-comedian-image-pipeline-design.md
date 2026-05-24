# Official-Site Comedian Image Pipeline Design

## Goal

Build a scalable admin pipeline for sourcing, reviewing, and publishing comedian headshots from official comedian websites. The pipeline should produce image assets that work for both current circular avatar clients and full-bleed hero clients.

The first implementation should focus on a single-comedian admin workflow, not bulk automation. It must keep a human approval step before publishing an image.

## Current State

Comedian images currently rely on:

- `Comedian.hasImage`
- a derived Bunny CDN URL based on the comedian display name:
  `https://{BUNNYCDN_CDN_HOST}/comedians/{encodeURIComponent(name)}.png`

This is not scalable because:

- image paths break or become stale when display names change;
- one square-ish PNG is used for both circular avatars and large heroes;
- there is no explicit asset metadata, source URL, active version, or crop history;
- existing CDN audit tooling checks only whether the old PNG exists, not whether it is high quality or client-ready.

## Client Image Requirements

Current web clients need at least two variants:

- **Avatar variant:** square `1:1`, intended for circular grid cards, compact cards, lineup tiles, and show-card lineup imagery.
- **Hero variant:** landscape `16:9`, intended for full-bleed comedian hero surfaces.

Initial output sizes:

- `avatar`: `1000x1000`
- `hero`: `2000x1125`

Both variants should be generated from the selected source image with `sharp`. The first pass should use automatic attention/entropy cropping. Manual focal-point or crop editing is explicitly deferred.

## Data Model

Add an image asset record rather than extending the old name-based convention.

Proposed model:

```prisma
model ComedianImageAsset {
  id             String   @id @default(cuid())
  comedianId     Int      @map("comedian_id")
  sourceUrl      String   @map("source_url")
  sourcePageUrl  String?  @map("source_page_url")
  originalPath   String   @map("original_path")
  avatarPath     String   @map("avatar_path")
  heroPath       String   @map("hero_path")
  width          Int?
  height         Int?
  mimeType       String?  @map("mime_type")
  status         String   @default("active")
  isActive       Boolean  @default(false) @map("is_active")
  createdBy      String?  @map("created_by")
  createdAt      DateTime @default(now()) @map("created_at") @db.Timestamptz

  comedian       Comedian @relation(fields: [comedianId], references: [id], onDelete: Cascade)

  @@index([comedianId, isActive])
  @@map("comedian_image_assets")
}
```

Add the reverse relation to `Comedian`.

Keep `Comedian.hasImage` for compatibility during migration. Public data builders should prefer the active `ComedianImageAsset` paths when present and fall back to the legacy `{name}.png` URL when no active asset exists.

## Storage Paths

Use stable ID-based paths, not display names.

Proposed Bunny storage paths:

- original: `comedian-images/{comedianId}/{assetId}/original`
- avatar: `comedian-images/{comedianId}/{assetId}/avatar.jpg`
- hero: `comedian-images/{comedianId}/{assetId}/hero.jpg`

Use JPEG for generated variants because comedian headshots are photographic and do not need transparency. Use quality around `85`, progressive JPEG if supported by `sharp`.

## Official-Site Candidate Discovery

The admin starts candidate discovery from a comedian row. The API uses the comedian's `website` and `websiteScrapingUrl` as seeds.

The crawler should inspect the seed page plus likely official-site paths when same-origin:

- `/about`
- `/bio`
- `/press`
- `/media`
- `/photos`
- `/photo`
- `/epk`
- `/contact`

Candidate sources:

- `og:image`
- `twitter:image`
- JSON-LD `image`
- `<img>` tags
- linked image files from obvious press/media pages

The crawler should resolve relative URLs against the source page and deduplicate by normalized image URL.

## Candidate Scoring

Each candidate should include enough evidence for admin review:

- image URL
- source page URL
- title or alt text if available
- width and height when known after inspection
- mime type
- score
- scoring reasons

Positive signals:

- URL/path/alt text contains `headshot`, `press`, `bio`, `portrait`, `media`, `photo`, `photos`, or the comedian's name;
- source is same-origin or a known CDN referenced by the official site;
- image is large enough for at least the avatar variant;
- aspect ratio can support avatar and preferably hero crops;
- image appears near the comedian's name or bio/press content.

Negative signals:

- URL/path/alt text contains `logo`, `icon`, `poster`, `flyer`, `banner`, `tour`, `merch`, `album`, `podcast`, or `sponsor`;
- image is too small;
- image is very wide or very narrow in a way that makes headshot cropping unlikely;
- source page appears unrelated to the official site.

Do not publish candidates automatically.

## Admin UX

On `/admin/comedians`, each row should show:

- current image state;
- current avatar preview if an active asset or legacy image exists;
- current hero preview if an active asset exists;
- actions for image sourcing.

Primary workflow:

1. Admin clicks `Find official-site images`.
2. The row shows loading state.
3. API returns ranked candidates.
4. Admin reviews candidate cards with preview, dimensions, score, and reasons.
5. Admin selects one candidate.
6. API generates temporary avatar and hero preview outputs.
7. Admin sees circular avatar preview and hero preview.
8. Admin confirms `Publish active image`.
9. API uploads original plus variants, marks the new asset active, marks old assets inactive, sets `hasImage=true`, writes audit entry, and revalidates public comedian surfaces.

The first pass does not need a drag-based crop editor.

## API Shape

Add admin-only endpoints under `/api/admin/comedians/images`.

Candidate discovery:

```http
POST /api/admin/comedians/images/discover
{
  "comedianId": 123
}
```

Response:

```json
{
  "ok": true,
  "candidates": [
    {
      "imageUrl": "https://example.com/press/headshot.jpg",
      "sourcePageUrl": "https://example.com/press",
      "width": 1800,
      "height": 2400,
      "mimeType": "image/jpeg",
      "score": 92,
      "reasons": ["headshot path", "same origin", "large portrait"]
    }
  ]
}
```

Publish:

```http
POST /api/admin/comedians/images/publish
{
  "comedianId": 123,
  "imageUrl": "https://example.com/press/headshot.jpg",
  "sourcePageUrl": "https://example.com/press"
}
```

The publish endpoint downloads the selected image again, validates it, generates variants, uploads them, updates DB state, and returns the active asset.

Preview:

```http
POST /api/admin/comedians/images/preview
{
  "comedianId": 123,
  "imageUrl": "https://example.com/press/headshot.jpg",
  "sourcePageUrl": "https://example.com/press"
}
```

The preview endpoint downloads and validates the selected image, generates avatar and hero crops, and returns temporary data URLs or short-lived same-origin preview URLs. It must not mutate the database or upload active Bunny assets.

## Validation And Safety

Admin endpoints must use `requireAdminForApi`.

Download constraints:

- only `http` and `https` URLs;
- reject private/local network hosts;
- maximum response size limit;
- timeout;
- image MIME types only;
- decode and validate with `sharp`;
- reject images below a minimum useful size.

Minimum source size:

- accept for avatar if at least `1000x1000` effective crop is possible;
- prefer for hero if at least `2000x1125` effective crop is possible;
- show a warning when the source is below the preferred hero size. The first pass can still generate the best possible crop after admin review instead of blocking publish.

## Revalidation

Publishing an image should revalidate the same comedian surfaces used by existing admin comedian updates:

- `comedian-search-data`
- `comedian-detail-data`
- `comedian-metadata`
- comedian name tag

If public data builders add asset path support, ensure both search and detail pages can see the active asset immediately after publish.

## Audit Trail

Publishing should write `AdminActionAudit` with:

- `action`: `comedian_image.publish`
- `entityType`: `comedian`
- `entityId`: comedian id
- `before`: previous active asset and legacy `hasImage`
- `after`: new active asset metadata

Discovery-only actions do not need audit records unless they mutate state.

## Testing

Backend tests:

- requires admin access;
- rejects invalid URL payloads;
- discovery ranks obvious headshot candidates above poster/logo candidates;
- publish downloads a mocked image, generates avatar and hero variants, uploads expected Bunny paths, marks prior assets inactive, creates a new active asset, sets `hasImage=true`, and writes audit;
- publish handles download, decode, and upload failures without partial active state.

Frontend tests:

- comedian rows show current image state;
- `Find official-site images` displays ranked candidates;
- selecting a candidate calls publish;
- successful publish updates the row preview and status;
- errors render a useful message and preserve current state.

## Deferred Work

- bulk crawling across all comedians;
- Google Images candidate discovery;
- manual crop editor and focal-point persistence;
- file upload from local disk;
- automated migration of existing name-based PNGs into `ComedianImageAsset`;
- separate background queue for long-running discovery.
