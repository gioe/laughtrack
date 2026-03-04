# Prisma Schema Domain Reference

Documents the purpose and usage of each model in `schema.prisma`.

## Core Entities

### Club
Comedy club venue. Has shows, tags, email subscriptions, and processed emails.

### Comedian
Individual comedian. Has social media stats, popularity, alternate names (aliases), favorites, and lineup appearances.

### Show
A comedy show at a club on a date. Has lineup items, tickets, and tags.

### Ticket
A ticket option for a show (price, purchase URL, type, sold-out flag).

### LineupItem
Join table linking a Comedian to a Show.

## User & Auth

### User
NextAuth user record (email, name, image).

### UserProfile
Extended user profile (role, zip code, notification preferences, favorite comedians).

### Account
OAuth account linked to a User (provider, tokens).

### VerificationToken
Email verification tokens for NextAuth.

### FavoriteComedian
User's favorited comedians (join table: UserProfile ↔ Comedian).

## Tagging

### Tag
A tag with type, name, slug, and visibility. Can be applied to clubs, shows, or comedians.

### TaggedClub
Join table: Club ↔ Tag.

### TaggedShow
Join table: Show ↔ Tag.

### TaggedComedian
Join table: Comedian ↔ Tag.

## Email Ingestion

### EmailSubscription
Tracks newsletter email subscriptions per club. One subscription per club (`clubId` unique).

**Fields:**
- `clubId` — FK to Club (unique; one subscription per club)
- `senderDomain` — email domain to expect newsletters from (e.g. `"thecomedystore.com"`)
- `subscribed` — whether the subscription is active (default `true`)
- `lastReceived` — timestamp of the last successfully received email (nullable)
- `createdAt` — when the subscription was created

**Usage:** Ingestion pipeline checks `subscribed` before processing emails from a given sender domain. `lastReceived` is updated each time an email from this club is successfully processed.

### ProcessedEmail
Deduplication log for ingested newsletter emails. Prevents re-ingesting the same message.

**Fields:**
- `messageId` — unique email Message-ID header value (unique index)
- `clubId` — FK to Club
- `receivedAt` — timestamp from the email headers
- `processedAt` — when the scraper processed the email (default `now()`)

**Usage:** Before processing any email, check whether `messageId` already exists in this table. If so, skip. After processing, insert a new row to mark the email as done.
