import { db } from "@/lib/db";
import { ClubDTO } from "@/objects/class/club/club.interface";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { buildClubImageUrl } from "@/util/imageUtil";
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
        return {
            name: clubData.name,
            id: clubData.id,
            imageUrl: buildClubImageUrl(clubData.name, clubData.hasImage),
            website: clubData.website,
            address: clubData.address,
            city: clubData.city ?? undefined,
            state: clubData.state ?? undefined,
            zipCode: clubData.zipCode,
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
