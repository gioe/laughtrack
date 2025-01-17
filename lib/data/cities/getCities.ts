import { db } from "@/lib/db";

export interface CityDTO {
    id: number;
    name: string;
}

export async function getCities(): Promise<CityDTO[]> {
    return db.city.findMany({
        select: {
            id: true,
            name: true
        }
    })
}
