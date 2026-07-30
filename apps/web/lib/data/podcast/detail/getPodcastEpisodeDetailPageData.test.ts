import { beforeEach, describe, expect, it, vi } from "vitest";
import { NotFoundError } from "../../../../objects/NotFoundError";

const { mockFindFirst, mockQueryRaw } = vi.hoisted(() => ({
    mockFindFirst: vi.fn(),
    mockQueryRaw: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: {
        $queryRaw: mockQueryRaw,
        podcastEpisode: {
            findFirst: mockFindFirst,
        },
    },
}));

import { getPodcastEpisodeDetailPageData } from "./getPodcastEpisodeDetailPageData";

beforeEach(() => {
    vi.clearAllMocks();
    mockFindFirst.mockResolvedValue(null);
    mockQueryRaw.mockResolvedValue([]);
});

describe("getPodcastEpisodeDetailPageData", () => {
    it("loads an episode directly while enforcing public podcast and accepted appearance rules", async () => {
        mockQueryRaw.mockResolvedValue([{ podcast_id: 99 }]);
        mockFindFirst.mockResolvedValue({
            id: 501,
            title: "Comedy Cellar Stories",
            description: "<p>A set recap &amp; debrief.</p>",
            releaseDate: new Date("2026-03-01T00:00:00.000Z"),
            durationSeconds: 3_720,
            episodeUrl: "https://pod.example/cellar",
            audioUrl: "https://cdn.example.com/cellar.mp3",
            appearances: [
                {
                    comedian: {
                        id: 101,
                        uuid: "demo-comedian-101",
                        name: "Guest Comic",
                        hasImage: true,
                    },
                },
            ],
            podcast: {
                id: 42,
                slug: "jane-show",
                title: "The Jane Show",
                authorName: "Jane Comic",
                websiteUrl: "https://pod.example",
                feedUrl: "https://pod.example/feed.xml",
                imageUrl: "https://cdn.example.com/podcast.jpg",
                description: "<p>Comedy interviews &amp; stories.</p>",
                comedianPodcasts: [
                    {
                        associationType: "cohost",
                        comedian: {
                            id: 7,
                            uuid: "uuid-7",
                            name: "Co Host",
                            hasImage: false,
                        },
                    },
                    {
                        associationType: "host",
                        comedian: {
                            id: 8,
                            uuid: "uuid-8",
                            name: "Main Host",
                            hasImage: true,
                        },
                    },
                ],
                _count: { episodes: 75 },
            },
        });

        const result = await getPodcastEpisodeDetailPageData(501);

        expect(mockFindFirst).toHaveBeenCalledWith(
            expect.objectContaining({
                where: expect.objectContaining({
                    id: 501,
                    podcast: {
                        is: expect.objectContaining({
                            denyListEntries: {
                                none: {
                                    restoredAt: null,
                                },
                            },
                            AND: [{ id: { notIn: [99] } }],
                        }),
                    },
                }),
                select: expect.objectContaining({
                    appearances: expect.objectContaining({
                        where: {
                            reviewStatus: "accepted",
                            comedian: { visible: true },
                        },
                    }),
                    podcast: expect.any(Object),
                }),
            }),
        );
        const query = mockFindFirst.mock.calls[0][0];
        expect(query).not.toHaveProperty("take");
        expect(query.select).not.toHaveProperty("episodes");

        expect(result).toEqual({
            podcast: {
                id: 42,
                slug: "jane-show",
                title: "The Jane Show",
                authorName: "Jane Comic",
                websiteUrl: "https://pod.example",
                feedUrl: "https://pod.example/feed.xml",
                imageUrl:
                    "/api/v1/podcast-artwork?url=https%3A%2F%2Fcdn.example.com%2Fpodcast.jpg",
                description: "Comedy interviews & stories.",
                episodeCount: 75,
                hosts: [
                    {
                        id: 8,
                        uuid: "uuid-8",
                        name: "Main Host",
                        imageUrl:
                            "https://test.b-cdn.net/comedians/Main%20Host.png",
                    },
                ],
            },
            episode: {
                id: 501,
                title: "Comedy Cellar Stories",
                description: "A set recap & debrief.",
                releaseDate: new Date("2026-03-01T00:00:00.000Z"),
                durationSeconds: 3_720,
                episodeUrl: "https://pod.example/cellar",
                audioUrl: "https://cdn.example.com/cellar.mp3",
                appearances: [
                    {
                        id: 101,
                        uuid: "demo-comedian-101",
                        name: "Guest Comic",
                        imageUrl:
                            "https://test.b-cdn.net/comedians/Guest%20Comic.png",
                    },
                ],
            },
        });
        expect(result.podcast).not.toHaveProperty("isFavorite");
    });

    it("uses accepted co-hosts when no accepted host exists and sorts them by name", async () => {
        mockFindFirst.mockResolvedValue({
            id: 501,
            title: "An Episode",
            description: null,
            releaseDate: null,
            durationSeconds: null,
            episodeUrl: null,
            audioUrl: null,
            appearances: [],
            podcast: {
                id: 42,
                slug: "jane-show",
                title: "The Jane Show",
                authorName: null,
                websiteUrl: null,
                feedUrl: null,
                imageUrl: null,
                description: null,
                comedianPodcasts: [
                    {
                        associationType: "cohost",
                        comedian: {
                            id: 7,
                            uuid: "uuid-7",
                            name: "Zed Host",
                            hasImage: false,
                        },
                    },
                    {
                        associationType: "cohost",
                        comedian: {
                            id: 8,
                            uuid: "uuid-8",
                            name: "Amy Host",
                            hasImage: false,
                        },
                    },
                ],
                _count: { episodes: 1 },
            },
        });

        const result = await getPodcastEpisodeDetailPageData(501);

        expect(result.podcast.hosts.map((host) => host.name)).toEqual([
            "Amy Host",
            "Zed Host",
        ]);
    });

    it("returns not found when the episode is missing or its podcast is not public", async () => {
        await expect(getPodcastEpisodeDetailPageData(501)).rejects.toThrow(
            NotFoundError,
        );
    });
});
