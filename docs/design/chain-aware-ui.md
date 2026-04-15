# Chain-Aware UI — Design Spec

## Context

The `Chain` model already exists in Prisma (`chains` table) with 10 chains covering 77 clubs.
This spec defines how chain relationships surface in the frontend.

---

## 1. Club Detail Page — Chain Badge + Sibling Links

### Chain Badge

Display a small badge below the club name (inside the hero overlay area) when the club belongs to a chain.

**Placement:** Between the club name (`<h1>`) and the location line (`MapPin` row) in `ClubDetailHeader`.

**Design:**
```
┌──────────────────────────────────────┐
│  [hero image]                        │
│                                      │
│  The Improv - Houston                │  ← h1
│  Part of the Improv family           │  ← chain badge (new)
│  📍 Houston, TX                      │  ← existing location
└──────────────────────────────────────┘
```

- Text: `Part of the {chain.name} family`
- Style: `text-sm text-white/60 italic` — subtle, secondary to the name and location
- The chain name is a link to `/chain/{chain.slug}` (future chain landing page) or,
  as an MVP, an anchor that scrolls to the "Other Locations" section below
- No badge shown when `chainId` is null (independent clubs)

### Sibling Locations Section

Add an "Other {chain.name} Locations" section below `ClubDataColumn` (contact info), before the filter bar.

**Design:**
```
Other Improv Locations
├── Improv - Atlanta          Houston, TX    →
├── Improv - Irvine           Irvine, CA     →
├── Improv - Pittsburgh       Pittsburgh, PA →
└── + 8 more locations                       →
```

- Horizontal scroll on mobile, 2-column grid on tablet, 3-column on desktop
- Each item: club name, city/state, linked to `/club/{clubName}`
- Show max 6 siblings; if more, show a "See all {n} locations" link
- Exclude the current club from the list
- Sort siblings alphabetically by name
- Section hidden entirely for non-chain clubs

**Data requirements:**
- `findClubByName` must include `chain: { select: { id, name, slug } }` in its select
- New query: `findSiblingClubs(chainId, excludeClubId)` returning `{ name, city, state, hasImage }[]`

---

## 2. Club Search Page — Chain Filter

### Recommendation: Add chain as a dedicated filter (not via Tags)

**Rationale:** Tags are community/editorial labels ("Best Open Mics", "Late Night"). Chains are
structural data — a club either belongs to a chain or it doesn't. Mixing chains into the Tag
system would:
- Require manual Tag creation for each chain (and keeping them in sync)
- Lose the ability to query chain membership via Prisma relations
- Conflate two different concepts in the filter UI

### Filter Design

Add a "Chain" dropdown/select in the FilterBar for `SearchVariant.AllClubs`.

**Placement:** After the existing tag filters, as a separate filter control.

```
[Sort ▾]  [Tags ▾]  [Chain ▾]  [Search...]
                      ├── All chains
                      ├── Improv (21)
                      ├── Funny Bone (11)
                      ├── Comedy Zone (8)
                      ├── Wiseguys (8)
                      ├── Laugh Factory (7)
                      ├── Helium (6)
                      └── ...
```

- URL param: `chain=improv` (uses chain slug)
- Single-select (a club can only belong to one chain)
- Show club count per chain in the dropdown
- When active, shows a removable chip like tag filters: `✕ Improv`
- Cleared by selecting "All chains" or removing the chip

**Data requirements:**
- New query: `getChainFilters()` returning `{ id, name, slug, clubCount }[]`
- `findClubsWithCount` must accept optional `chainSlug` param and add `WHERE chain.slug = ?`
- `QueryHelper` needs `getChainClause()` method

### Search Result Cards

On each club card in search results, show a subtle chain indicator:

```
┌─────────────────────┐
│  [club image]       │
│  Helium Comedy Club │
│  Philadelphia, PA   │
│  Helium             │  ← chain name, muted text
│  12 upcoming shows  │
└─────────────────────┘
```

- Text: chain name only (e.g., "Helium"), in `text-xs text-base-content/50`
- Hidden for non-chain clubs (no empty row)
- Requires `chainName` on `ClubDTO`

---

## 3. Data Model Changes Summary

### ClubDTO additions
```ts
export interface ClubDTO {
    // ... existing fields ...
    chainId?: number | null;
    chainName?: string | null;
    chainSlug?: string | null;
}
```

### New/modified queries
| Query | Change |
|-------|--------|
| `findClubByName` | Add `chain: { select: { id: true, name: true, slug: true } }` to CLUB_SELECT |
| `findClubsWithCount` | Add `chainId`, `chainName` to select; accept `chain` filter param |
| `findSiblingClubs` (new) | `WHERE chainId = ? AND id != ? AND visible = true`, select name/city/state/hasImage |
| `getChainFilters` (new) | `SELECT chain.*, COUNT(clubs) WHERE visible = true GROUP BY chain.id` |

### URL parameters
| Param | Page | Type | Example |
|-------|------|------|---------|
| `chain` | `/club/search` | single slug | `?chain=improv` |

---

## 4. Pages NOT affected

- **Comedian detail/search** — no chain relationship
- **Show detail/search** — shows inherit chain via club; no direct UI needed now
- **Homepage** — "Popular Clubs" section unchanged (chain badge would add clutter to the compact card)

---

## 5. Future considerations (out of scope)

- `/chain/{slug}` landing page (all clubs in a chain, with chain logo/description)
- Chain logo/icon in the badge
- "Chains near you" section on homepage
- Cross-chain show search ("all Improv shows this weekend")
