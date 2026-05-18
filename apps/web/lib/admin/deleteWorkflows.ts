import { Prisma } from "@prisma/client";

export const ADMIN_DELETE_ENTITY_TYPES = [
    "club",
    "show",
    "comedian",
    "podcast",
] as const;

export type AdminDeleteEntityType = (typeof ADMIN_DELETE_ENTITY_TYPES)[number];

export type AdminDeleteDependency = {
    key: string;
    label: string;
    count: number;
};

export type AdminDeletePreview = {
    entityType: AdminDeleteEntityType;
    entityId: number;
    label: string;
    before: Prisma.InputJsonValue;
    dependencies: AdminDeleteDependency[];
};

type AdminDeleteWorkflow = {
    preview: (
        tx: Prisma.TransactionClient,
        entityId: number,
    ) => Promise<AdminDeletePreview | null>;
    delete: (tx: Prisma.TransactionClient, entityId: number) => Promise<void>;
    revalidationTags: (preview: AdminDeletePreview) => string[];
};

function dependency(
    key: string,
    label: string,
    count: number,
): AdminDeleteDependency {
    return { key, label, count };
}

function compactDependencies(
    dependencies: AdminDeleteDependency[],
): AdminDeleteDependency[] {
    return dependencies.filter((dep) => dep.count > 0);
}

async function previewClub(
    tx: Prisma.TransactionClient,
    entityId: number,
): Promise<AdminDeletePreview | null> {
    const club = await tx.club.findUnique({
        where: { id: entityId },
        select: {
            id: true,
            name: true,
            address: true,
            website: true,
            visible: true,
            totalShows: true,
            status: true,
        },
    });
    if (!club) return null;

    const [
        shows,
        tickets,
        lineupItems,
        taggedShows,
        showNotifications,
        scrapingSources,
        taggedClubs,
        emailSubscriptions,
        processedEmails,
        productionCompanyVenues,
        aliases,
    ] = await Promise.all([
        tx.show.count({ where: { clubId: entityId } }),
        tx.ticket.count({ where: { show: { clubId: entityId } } }),
        tx.lineupItem.count({ where: { show: { clubId: entityId } } }),
        tx.taggedShow.count({ where: { show: { clubId: entityId } } }),
        tx.sentNotification.count({ where: { show: { clubId: entityId } } }),
        tx.scrapingSource.count({ where: { clubId: entityId } }),
        tx.taggedClub.count({ where: { clubId: entityId } }),
        tx.emailSubscription.count({ where: { clubId: entityId } }),
        tx.processedEmail.count({ where: { clubId: entityId } }),
        tx.productionCompanyVenue.count({ where: { clubId: entityId } }),
        tx.clubAlias.count({ where: { clubId: entityId } }),
    ]);

    return {
        entityType: "club",
        entityId,
        label: club.name,
        before: club,
        dependencies: compactDependencies([
            dependency("shows", "Shows", shows),
            dependency("tickets", "Tickets", tickets),
            dependency("lineupItems", "Lineup items", lineupItems),
            dependency("taggedShows", "Show tags", taggedShows),
            dependency(
                "showNotifications",
                "Sent notifications",
                showNotifications,
            ),
            dependency("scrapingSources", "Scraping sources", scrapingSources),
            dependency("taggedClubs", "Club tags", taggedClubs),
            dependency(
                "emailSubscriptions",
                "Email subscriptions",
                emailSubscriptions,
            ),
            dependency("processedEmails", "Processed emails", processedEmails),
            dependency(
                "productionCompanyVenues",
                "Production company venue links",
                productionCompanyVenues,
            ),
            dependency("aliases", "Aliases", aliases),
        ]),
    };
}

async function previewShow(
    tx: Prisma.TransactionClient,
    entityId: number,
): Promise<AdminDeletePreview | null> {
    const show = await tx.show.findUnique({
        where: { id: entityId },
        select: {
            id: true,
            name: true,
            date: true,
            showPageUrl: true,
            clubId: true,
            club: { select: { name: true } },
        },
    });
    if (!show) return null;

    const [tickets, lineupItems, taggedShows, sentNotifications] =
        await Promise.all([
            tx.ticket.count({ where: { showId: entityId } }),
            tx.lineupItem.count({ where: { showId: entityId } }),
            tx.taggedShow.count({ where: { showId: entityId } }),
            tx.sentNotification.count({ where: { showId: entityId } }),
        ]);
    const label =
        show.name ?? `${show.club.name} on ${show.date.toISOString()}`;

    return {
        entityType: "show",
        entityId,
        label,
        before: {
            id: show.id,
            name: show.name,
            date: show.date.toISOString(),
            showPageUrl: show.showPageUrl,
            clubId: show.clubId,
            clubName: show.club.name,
        },
        dependencies: compactDependencies([
            dependency("tickets", "Tickets", tickets),
            dependency("lineupItems", "Lineup items", lineupItems),
            dependency("taggedShows", "Show tags", taggedShows),
            dependency(
                "sentNotifications",
                "Sent notifications",
                sentNotifications,
            ),
        ]),
    };
}

async function previewComedian(
    tx: Prisma.TransactionClient,
    entityId: number,
): Promise<AdminDeletePreview | null> {
    const comedian = await tx.comedian.findUnique({
        where: { id: entityId },
        select: {
            id: true,
            uuid: true,
            name: true,
            instagramAccount: true,
            tiktokAccount: true,
            website: true,
            totalShows: true,
            parentComedianId: true,
        },
    });
    if (!comedian) return null;

    const [
        alternativeNames,
        favoriteComedians,
        lineupItems,
        taggedComedians,
        sentNotifications,
        podcastAppearances,
        podcastIdentityLinks,
        comedianPodcasts,
        podcastCandidateReviews,
        episodeAppearances,
        episodeAppearanceReviews,
    ] = await Promise.all([
        tx.comedian.count({ where: { parentComedianId: entityId } }),
        tx.favoriteComedian.count({ where: { comedianId: comedian.uuid } }),
        tx.lineupItem.count({ where: { comedianId: comedian.uuid } }),
        tx.taggedComedian.count({ where: { comedianId: comedian.uuid } }),
        tx.sentNotification.count({ where: { comedianId: comedian.uuid } }),
        tx.comedianPodcastAppearance.count({ where: { comedianId: entityId } }),
        tx.comedianPodcastIdentityLink.count({
            where: { comedianId: entityId },
        }),
        tx.comedianPodcast.count({ where: { comedianId: entityId } }),
        tx.podcastCandidateReview.count({ where: { comedianId: entityId } }),
        tx.episodeAppearance.count({ where: { comedianId: entityId } }),
        tx.episodeAppearanceReview.count({ where: { comedianId: entityId } }),
    ]);

    return {
        entityType: "comedian",
        entityId,
        label: comedian.name,
        before: comedian,
        dependencies: compactDependencies([
            dependency(
                "alternativeNames",
                "Alternative names",
                alternativeNames,
            ),
            dependency("favoriteComedians", "Favorites", favoriteComedians),
            dependency("lineupItems", "Lineup items", lineupItems),
            dependency("taggedComedians", "Comedian tags", taggedComedians),
            dependency(
                "sentNotifications",
                "Sent notifications",
                sentNotifications,
            ),
            dependency(
                "podcastAppearances",
                "Legacy podcast appearances",
                podcastAppearances,
            ),
            dependency(
                "podcastIdentityLinks",
                "Podcast identity links",
                podcastIdentityLinks,
            ),
            dependency("comedianPodcasts", "Podcast links", comedianPodcasts),
            dependency(
                "podcastCandidateReviews",
                "Podcast candidate reviews",
                podcastCandidateReviews,
            ),
            dependency(
                "episodeAppearances",
                "Episode appearances",
                episodeAppearances,
            ),
            dependency(
                "episodeAppearanceReviews",
                "Episode appearance reviews",
                episodeAppearanceReviews,
            ),
        ]),
    };
}

async function previewPodcast(
    tx: Prisma.TransactionClient,
    entityId: number,
): Promise<AdminDeletePreview | null> {
    const podcast = await tx.podcast.findUnique({
        where: { id: entityId },
        select: {
            id: true,
            slug: true,
            source: true,
            sourcePodcastId: true,
            title: true,
            authorName: true,
            websiteUrl: true,
            feedUrl: true,
            lastSyncedAt: true,
        },
    });
    if (!podcast) return null;

    const [
        episodes,
        episodeAppearances,
        episodeAppearanceReviews,
        comedianPodcasts,
        candidateReviews,
    ] = await Promise.all([
        tx.podcastEpisode.count({ where: { podcastId: entityId } }),
        tx.episodeAppearance.count({
            where: { episode: { podcastId: entityId } },
        }),
        tx.episodeAppearanceReview.count({
            where: { episode: { podcastId: entityId } },
        }),
        tx.comedianPodcast.count({ where: { podcastId: entityId } }),
        tx.podcastCandidateReview.count({ where: { podcastId: entityId } }),
    ]);

    return {
        entityType: "podcast",
        entityId,
        label: podcast.title,
        before: {
            id: podcast.id,
            slug: podcast.slug,
            source: podcast.source,
            sourcePodcastId: podcast.sourcePodcastId,
            title: podcast.title,
            authorName: podcast.authorName,
            websiteUrl: podcast.websiteUrl,
            feedUrl: podcast.feedUrl,
            lastSyncedAt: podcast.lastSyncedAt?.toISOString() ?? null,
        },
        dependencies: compactDependencies([
            dependency("episodes", "Episodes", episodes),
            dependency(
                "episodeAppearances",
                "Episode appearances",
                episodeAppearances,
            ),
            dependency(
                "episodeAppearanceReviews",
                "Episode appearance reviews",
                episodeAppearanceReviews,
            ),
            dependency(
                "comedianPodcasts",
                "Comedian podcast links",
                comedianPodcasts,
            ),
            dependency(
                "candidateReviews",
                "Podcast candidate reviews retained with podcast cleared",
                candidateReviews,
            ),
        ]),
    };
}

export const adminDeleteWorkflows: Record<
    AdminDeleteEntityType,
    AdminDeleteWorkflow
> = {
    club: {
        preview: previewClub,
        delete: async (tx, entityId) => {
            await tx.club.delete({ where: { id: entityId } });
        },
        revalidationTags: (preview) => [
            "club-detail-data",
            "club-metadata",
            preview.label,
        ],
    },
    show: {
        preview: previewShow,
        delete: async (tx, entityId) => {
            await tx.show.delete({ where: { id: entityId } });
        },
        revalidationTags: () => ["shows-search", "home-feed"],
    },
    comedian: {
        preview: previewComedian,
        delete: async (tx, entityId) => {
            await tx.comedian.delete({ where: { id: entityId } });
        },
        revalidationTags: (preview) => [
            "comedian-detail-data",
            "comedian-metadata",
            preview.label,
        ],
    },
    podcast: {
        preview: previewPodcast,
        delete: async (tx, entityId) => {
            await tx.podcast.delete({ where: { id: entityId } });
        },
        revalidationTags: (preview) => [
            "podcast-detail-data",
            "podcast-metadata",
            preview.label,
        ],
    },
};
