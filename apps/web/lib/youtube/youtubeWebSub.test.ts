import { describe, expect, it } from "vitest";

import { parseYouTubeWebSubFeed } from "./youtubeWebSub";

describe("parseYouTubeWebSubFeed", () => {
    it("extracts YouTube Atom entry metadata from WebSub feed payloads", () => {
        const xml = `<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns="http://www.w3.org/2005/Atom">
  <link rel="hub" href="https://pubsubhubbub.appspot.com"/>
  <link rel="self" href="https://www.youtube.com/feeds/videos.xml?channel_id=UC-live-channel"/>
  <entry>
    <id>yt:video:abc123</id>
    <yt:videoId>abc123</yt:videoId>
    <yt:channelId>UC-live-channel</yt:channelId>
    <title>Late set &amp; crowd work</title>
    <link rel="alternate" href="https://www.youtube.com/watch?v=abc123"/>
    <author>
      <name>Comedian Channel</name>
      <uri>https://www.youtube.com/channel/UC-live-channel</uri>
    </author>
    <published>2026-06-29T20:00:00+00:00</published>
    <updated>2026-06-29T20:01:30+00:00</updated>
  </entry>
  <entry>
    <id>yt:video:def456</id>
    <yt:videoId>def456</yt:videoId>
    <yt:channelId>UC-live-channel</yt:channelId>
    <title>Second entry</title>
    <link rel="alternate" href="https://www.youtube.com/watch?v=def456"/>
    <published>2026-06-29T21:00:00+00:00</published>
    <updated>2026-06-29T21:02:00+00:00</updated>
  </entry>
</feed>`;

        expect(parseYouTubeWebSubFeed(xml)).toEqual([
            {
                videoId: "abc123",
                channelId: "UC-live-channel",
                title: "Late set & crowd work",
                link: "https://www.youtube.com/watch?v=abc123",
                publishedAt: "2026-06-29T20:00:00+00:00",
                updatedAt: "2026-06-29T20:01:30+00:00",
            },
            {
                videoId: "def456",
                channelId: "UC-live-channel",
                title: "Second entry",
                link: "https://www.youtube.com/watch?v=def456",
                publishedAt: "2026-06-29T21:00:00+00:00",
                updatedAt: "2026-06-29T21:02:00+00:00",
            },
        ]);
    });

    it("returns an empty list when a notification payload has no entries", () => {
        expect(parseYouTubeWebSubFeed("<feed></feed>")).toEqual([]);
    });
});
