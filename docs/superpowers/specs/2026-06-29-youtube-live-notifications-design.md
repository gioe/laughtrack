# YouTube Live Push Notifications Design

## Goal

Notify a user when a comedian they follow goes live on YouTube.

The notification should be near real time without polling every followed channel. The system will use YouTube's WebSub hub (`https://pubsubhubbub.appspot.com/`) to receive channel feed updates, then confirm the specific video is currently live with the YouTube Data API before sending push notifications.

## Existing Context

LaughTrack already has:

- Favorite comedian relationships in `favorite_comedians`.
- User push opt-in state in `user_profiles.push_show_notifications`.
- Active device tokens in `user_push_tokens`.
- A push delivery implementation in the scraper notification service for APNs and FCM.
- A notification-center model based on `sent_notifications`, currently tied to show notifications through a required `show_id`.

The existing `sent_notifications` table is not a good fit for YouTube live notifications because it requires a show row. YouTube live notifications need their own event identity based on YouTube video ID and comedian ID.

## Architecture

The web app owns YouTube live webhook ingestion because Next.js API routes are the natural public HTTP callback surface and already have Prisma access for atomic dedupe and follower lookup.

The scraper-side push delivery code should be reused by extracting or mirroring its APNs/FCM sender behavior in the web app. The web callback should not depend on a long-running scraper command to complete normal notification delivery.

The core flow:

1. Store each comedian's canonical YouTube channel ID.
2. Subscribe active channel IDs to YouTube's WebSub hub with topic URLs of the form `https://www.youtube.com/xml/feeds/videos.xml?channel_id=CHANNEL_ID`.
3. Expose a callback route that handles WebSub verification challenges.
4. On Atom POST callbacks, parse `yt:videoId` and `yt:channelId`.
5. Look up comedians whose `youtube_channel_id` matches the callback channel ID.
6. Call YouTube Data API `videos.list` for the `videoId` with `part=snippet,liveStreamingDetails`.
7. Send notifications only when the API confirms `snippet.liveBroadcastContent === "live"` or `liveStreamingDetails.actualStartTime` is present and `actualEndTime` is absent.
8. Record one sent row per recipient, comedian, video, and channel so duplicate WebSub updates do not resend.

## Data Model

Add `youtube_channel_id` to `comedians`.

This should be distinct from the existing `youtube_account` field. `youtube_account` is used as a user-facing handle/account value, while WebSub topics require the canonical channel ID.

Add a new table for YouTube live notification sends named `youtube_live_notifications`:

- `id`
- `user_id`
- `comedian_id`
- `youtube_channel_id`
- `youtube_video_id`
- `video_title`
- `video_url`
- `notification_type`
- `sent_at`

Add a unique constraint on `(user_id, comedian_id, youtube_video_id, notification_type)`.

This table also becomes the source for notification-center history once the UI is extended to show non-show notification types.

## WebSub Subscription Management

Subscription creation and renewal should be a separate authenticated admin or scheduled task, not part of the webhook callback.

The subscription task should:

- Select comedians with a non-empty `youtube_channel_id`.
- POST subscribe requests to the WebSub hub.
- Use the public callback URL for `hub.callback`.
- Use the channel feed URL for `hub.topic`.
- Request a lease duration and renew before expiry.
- Log failures per channel without blocking other subscriptions.

Persisting subscription state is useful but can be incremental. The first version can safely be idempotent and renew all known channel subscriptions on a schedule.

## Callback Route

Add `/api/webhooks/youtube`.

GET handles hub verification:

- Echo `hub.challenge` when `hub.mode` is `subscribe` or `unsubscribe`.
- Validate the topic has the expected YouTube feed shape.
- Return `400` for missing challenge/topic parameters.

POST handles feed notifications:

- Read the raw XML body.
- Parse with an XML parser, not ad hoc string matching.
- Extract all feed entries because a callback may include more than one entry.
- For each entry, extract `yt:videoId`, `yt:channelId`, title, link, and published/updated timestamps when present.
- Ignore entries missing video ID or channel ID.
- Process entries independently so one bad entry does not drop the whole callback.

The route should return quickly after processing. If APNs/FCM latency becomes a problem, move delivery to a queued job, but the first version can deliver inline if the route has bounded work and logs failures.

## Live Verification

Use YouTube Data API `videos.list` rather than `search.list`.

Request:

`GET https://www.googleapis.com/youtube/v3/videos?part=snippet,liveStreamingDetails&id=VIDEO_ID&key=...`

Treat a video as live when:

- `snippet.liveBroadcastContent` is `"live"`, or
- `liveStreamingDetails.actualStartTime` exists and `liveStreamingDetails.actualEndTime` does not exist.

Treat `"upcoming"` and missing live details as not-yet-live. Because YouTube API state can lag behind WebSub notifications, store or schedule a small retry window for not-yet-live videos. A practical first version can retry a few times over several minutes before dropping the event.

## Recipient Selection

Notify users who:

- Follow the matched comedian in `favorite_comedians`.
- Have `user_profiles.push_show_notifications = true` for the first version.
- Have at least one active row in `user_push_tokens`.

The first version reuses the existing push opt-in instead of adding a separate live-stream preference. A later UI/settings pass can split show notifications and live-stream notifications into separate categories.

## Push Payload

Payload should identify the notification as a YouTube live event.

Suggested title:

`{comedianName} is live on YouTube`

Suggested body:

The video title when available, otherwise `Watch now`.

Suggested data:

- `type`: `youtube_live`
- `comedianId`
- `youtubeVideoId`
- `youtubeChannelId`
- `url`: `https://www.youtube.com/watch?v=VIDEO_ID`

iOS and Android should receive equivalent data keys so both apps can deep-link consistently.

## Deduplication

Deduplication happens before delivery by inserting or reserving the unique `(user_id, comedian_id, youtube_video_id, notification_type)` row.

If the insert succeeds, send the push. If it conflicts, skip delivery.

If push delivery fails because a device token is invalid, deactivate that token using the same invalid-token rules as existing show push notifications. The sent row can remain, because the event was processed for that user and should not be retried endlessly.

## Error Handling

Webhook verification errors should return `400`.

Malformed XML should return `400` and log the parse failure.

Unknown channel IDs should return `204` or `200` without notification sends.

YouTube API errors should be logged and counted. Quota or transient 5xx failures should not mark a notification as sent. Retryable verification failures should be retried through the same delayed verification path.

Push provider failures should not abort processing for other recipients or device tokens.

## Testing

Add route tests for:

- WebSub GET challenge success.
- WebSub GET missing challenge failure.
- POST ignores unknown channel IDs.
- POST extracts `yt:videoId` and `yt:channelId` from Atom XML.
- POST calls `videos.list` for the extracted video ID.
- Confirmed live videos notify only users who follow the comedian, have push opt-in enabled, and have active push tokens.
- Upcoming/non-live videos do not send immediately and are marked for retry.
- Duplicate callbacks do not send duplicate pushes.
- Invalid push tokens are deactivated.

Add unit tests for:

- YouTube feed XML parsing.
- YouTube video live-state classification.
- Push payload construction.

## Rollout

1. Add schema fields and migrations.
2. Implement parser and live-state verifier behind tests.
3. Implement callback route behind tests.
4. Implement push delivery integration.
5. Add subscription renewal command or admin task.
6. Populate `youtube_channel_id` for a small test set of comedians.
7. Subscribe those channels and verify callback delivery in production-like environment.
8. Expand channel coverage after notifications are observed and dedupe metrics look correct.

## Open Decisions Resolved

- Use PubSubHubbub/WebSub for near-real-time channel notifications.
- Use `videos.list` for cheap per-video live verification.
- Do not use `search.list` polling.
- Add canonical `youtube_channel_id` instead of relying on `youtube_account`.
- Use a dedicated YouTube live notification table instead of overloading show-specific `sent_notifications`.
- Use the existing push show opt-in for the first version.
