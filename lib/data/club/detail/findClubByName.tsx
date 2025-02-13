import { db } from "@/lib/db";
import { ClubDTO } from "@/objects/class/club/club.interface";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { buildClubImageUrl } from "@/util/imageUtil";

export async function findClubByName(helper: QueryHelper): Promise<ClubDTO> {
    const clubData = await db.club.findFirst({
        where: {
            name: helper.getNameSlug(),
        },
        select: {
            id: true,
            name: true,
            website: true,
            address: true,
            zipCode: true,
        },
    });

    if (!clubData) {
        throw new Error(`Club with name ${name} not found`);
    }

    return {
        name: clubData.name,
        id: clubData.id,
        imageUrl: buildClubImageUrl(clubData.name),
        website: clubData.website,
        address: clubData.address,
        zipCode: clubData.zipCode,
    };
}
