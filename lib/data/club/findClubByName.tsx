import { db } from "@/lib/db";
import { ClubDTO } from "@/objects/class/club/club.interface";
import { buildClubImageUrl } from "@/util/imageUtil";

export async function findClubByName(name: string): Promise<ClubDTO> {
    const clubData = await db.club.findFirst({
        where: {
            name: name,
        },
        select: {
            id: true,
            name: true,
            website: true,
            city: true,
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
        city: clubData.city.name,
        address: clubData.address,
        zipCode: clubData.zipCode,
    };
}
