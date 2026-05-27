import { db } from "@/lib/db";
import { ClubDTO } from "@/objects/class/club/club.interface";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { buildClubHeroImageUrl, buildClubImageUrl } from "@/util/imageUtil";
import { Prisma } from "@prisma/client";
import { NotFoundError } from "@/objects/NotFoundError";
import { ClosedClubError } from "@/objects/ClosedClubError";

const CLUB_SELECT = {
    id: true,
    name: true,
    website: true,
    address: true,
    city: true,
    state: true,
    zipCode: true,
    hasImage: true,
    status: true,
    closedAt: true,
    clubType: true,
    phoneNumber: true,
    description: true,
    hours: true,
    chain: {
        select: {
            id: true,
            name: true,
            slug: true,
        },
    },
    imageAssets: {
        where: { isActive: true },
        select: { heroPath: true },
        orderBy: { publishedAt: "desc" },
        take: 1,
    },
} as const;

export async function findClubByName(helper: QueryHelper): Promise<ClubDTO> {
    try {
        const name = helper.getSlug();
        if (!name) {
            throw new Error("Club name is required");
        }

        const clubData = await db.club.findFirst({
            where: {
                name: {
                    equals: name,
                    mode: Prisma.QueryMode.insensitive,
                },
            },
            select: CLUB_SELECT,
        });

        if (!clubData) {
            throw new NotFoundError(`Club with name "${name}" not found`);
        }

        if (clubData.status === "closed") {
            throw new ClosedClubError(clubData.name, clubData.closedAt);
        }
        const activeImageAsset = clubData.imageAssets[0] ?? null;
        return {
            name: clubData.name,
            id: clubData.id,
            imageUrl: buildClubImageUrl(clubData.name, clubData.hasImage),
            heroUrl: buildClubHeroImageUrl(activeImageAsset?.heroPath),
            website: clubData.website,
            address: clubData.address,
            city: clubData.city ?? undefined,
            state: clubData.state ?? undefined,
            zipCode: clubData.zipCode,
            phoneNumber: clubData.phoneNumber ?? undefined,
            description: clubData.description ?? undefined,
            hours: clubData.hours ?? undefined,
            chainId: clubData.chain?.id ?? null,
            chainName: clubData.chain?.name ?? null,
            chainSlug: clubData.chain?.slug ?? null,
            clubType: clubData.clubType,
        };
    } catch (error) {
        if (
            error instanceof ClosedClubError ||
            error instanceof NotFoundError
        ) {
            throw error;
        }
        if (error instanceof Error) {
            console.error("Error in findClubByName:", error);
            throw error;
        }
        throw new Error(
            "An unknown error occurred while fetching club details",
        );
    }
}
