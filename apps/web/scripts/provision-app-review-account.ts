import { PrismaClient } from "@prisma/client";
import { PrismaNeon } from "@prisma/adapter-neon";
import { neonConfig, Pool } from "@neondatabase/serverless";
import { WebSocket } from "ws";
import { config } from "dotenv";

const localEnv = config({ path: "../scraper/.env" }).parsed ?? {};
const email = process.env.APP_REVIEW_EMAIL?.trim().toLowerCase();

neonConfig.webSocketConstructor = WebSocket;

if (!email) {
    throw new Error("APP_REVIEW_EMAIL is required");
}
const reviewEmail = email;

const databaseUrl =
    process.env.DATABASE_URL ||
    `postgresql://${localEnv.DATABASE_USER}:${localEnv.DATABASE_PASSWORD}` +
        `@${localEnv.DATABASE_HOST}:${localEnv.DATABASE_PORT || "5432"}` +
        `/${localEnv.DATABASE_NAME}?sslmode=require`;

const pool = new Pool({ connectionString: databaseUrl });
const db = new PrismaClient({ adapter: new PrismaNeon(pool) });

async function main() {
    const user = await db.user.upsert({
        where: { email: reviewEmail },
        create: {
            email: reviewEmail,
            emailVerified: new Date(),
            name: "App Review",
            profile: {
                create: {
                    role: "user",
                    comedianOnboardingCompleted: true,
                    zipCode: "10001",
                    nearbyDistanceMiles: 25,
                },
            },
        },
        update: {
            profile: {
                upsert: {
                    create: {
                        role: "user",
                        comedianOnboardingCompleted: true,
                        zipCode: "10001",
                        nearbyDistanceMiles: 25,
                    },
                    update: {},
                },
            },
        },
        select: { id: true },
    });

    const profile = await db.userProfile.findUniqueOrThrow({
        where: { userid: user.id },
        select: { id: true },
    });
    const profileId = profile.id;
    const [comedians, clubs, podcasts] = await Promise.all([
        db.comedian.findMany({
            where: { visible: true, hasImage: true },
            orderBy: { popularity: "desc" },
            take: 3,
            select: { uuid: true },
        }),
        db.club.findMany({
            where: { visible: true, status: "active", hasImage: true },
            orderBy: { popularity: "desc" },
            take: 1,
            select: { id: true },
        }),
        db.podcast.findMany({
            where: {
                imageUrl: { not: null },
                denyListEntries: { none: { restoredAt: null } },
            },
            orderBy: { updatedAt: "desc" },
            take: 1,
            select: { id: true },
        }),
    ]);

    const [favoriteComedians, favoriteClubs, favoritePodcasts] =
        await Promise.all([
            db.favoriteComedian.createMany({
                data: comedians.map(({ uuid }) => ({
                    profileId,
                    comedianId: uuid,
                })),
                skipDuplicates: true,
            }),
            db.favoriteClub.createMany({
                data: clubs.map(({ id }) => ({ profileId, clubId: id })),
                skipDuplicates: true,
            }),
            db.favoritePodcast.createMany({
                data: podcasts.map(({ id }) => ({ profileId, podcastId: id })),
                skipDuplicates: true,
            }),
        ]);

    console.log(
        JSON.stringify({
            userId: user.id,
            seeded: {
                comedians: favoriteComedians.count,
                clubs: favoriteClubs.count,
                podcasts: favoritePodcasts.count,
            },
        }),
    );
}

main()
    .finally(async () => {
        await db.$disconnect();
        await pool.end();
    })
    .catch((error: unknown) => {
        console.error(error instanceof Error ? error.message : error);
        process.exitCode = 1;
    });
