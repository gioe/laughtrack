"use server";

import { getComediansByZip } from "@/lib/data/home/getComediansByZip";
import { DEFAULT_HOME_RADIUS_MILES } from "@/util/constants/radiusConstants";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";

export async function getComediansByZipAction(
    zipCode: string,
): Promise<ComedianDTO[]> {
    if (!/^\d{5}$/.test(zipCode)) return [];
    return getComediansByZip(zipCode, DEFAULT_HOME_RADIUS_MILES).catch(
        () => [],
    );
}
