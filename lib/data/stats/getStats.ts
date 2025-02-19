import { db } from "@/lib/db";
import { StatsDTO } from "./interface";

export async function getStats(): Promise<StatsDTO> {
    const [clubCount, comedianCount, showCount] = await Promise.all([
        db.club.count(),
        db.comedian.count(),
        db.show.count({
            where: {
                date: {
                    gt: new Date()
                }
            }
        })
    ]);

    return {
        clubCount,
        comedianCount,
        showCount
    };
}
