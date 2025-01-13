import { CityList } from "@/contexts/CityProvider";
import { db } from "@/lib/db";
import { CityDTO } from "@/objects/class/city/city.interface";

export async function getCities(): Promise<CityDTO[]> {
    return db.city.findMany({
        select: {
            id: true,
            name: true
        }
    })
}
