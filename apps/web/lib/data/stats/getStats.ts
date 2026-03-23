import { db } from "@/lib/db";
import { Prisma } from "@prisma/client";
import { StatsDTO, isValidStatsDTO } from "./interface";

/**
 * Fetches platform statistics including club, comedian, and show counts
 * @returns A promise that resolves to the platform statistics
 * @throws {Error} If there's an error fetching the statistics
 */
export async function getStats(): Promise<StatsDTO> {
    try {
        const [clubCount, comedianCount, showCount] = await Promise.all([
            db.club.count({
                where: {
                    visible: true,
                    status: "active",
                },
            }),
            db.comedian.count({
                where: {
                    taggedComedians: {
                        none: {
                            tag: {
                                restrictContent: true,
                            },
                        },
                    },
                },
            }),
            db.show.count({
                where: {
                    date: {
                        gt: new Date(),
                    },
                },
            }),
        ]);

        const stats: StatsDTO = {
            clubCount,
            comedianCount,
            showCount,
        };

        // Validate the response data
        if (!isValidStatsDTO(stats)) {
            throw new Error("Invalid stats data received from database");
        }

        return stats;
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            console.error("Database error in getStats:", error);
            throw new Error(`Database error: ${error.message}`);
        }
        if (error instanceof Error) {
            console.error("Error in getStats:", error);
            throw error;
        }
        throw new Error("An unknown error occurred while fetching statistics");
    }
}
