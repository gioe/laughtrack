import { db } from "@/lib/db";
import {
    buildShowSelect,
    mapShowRowToDTO,
} from "@/lib/data/show/showSelect";
import { NotFoundError } from "@/objects/NotFoundError";
import { Prisma } from "@prisma/client";
import { ShowDetailDTO } from "./interface";

export interface FindShowByIdResult {
    show: ShowDetailDTO;
    clubId: number;
}

export async function findShowById(id: number): Promise<FindShowByIdResult> {
    try {
        // Shared public show select (TASK-3692), parameterized for the detail
        // page: description is emitted, and each lineup member's showCount
        // counts upcoming shows only (search/home count all-time lineup
        // items). Evaluated per request so the date boundary is "now".
        const baseSelect = buildShowSelect({
            includeDescription: true,
            lineupCountWhere: { show: { date: { gt: new Date() } } },
        });

        const row = await db.show.findUnique({
            where: { id },
            select: {
                ...baseSelect,
                showPageUrl: true,
                // `visible` feeds the hidden-club gate below; it stays out of
                // the shared select because the list paths (search/home)
                // filter club visibility in their WHERE clause instead.
                club: {
                    select: { ...baseSelect.club.select, visible: true },
                },
            },
        });

        if (!row) {
            throw new NotFoundError(`Show with id "${id}" not found`);
        }

        // Hidden clubs stay hidden on the show detail page too — don't leak
        // their shows just because the URL is guessable.
        if (!row.club.visible) {
            throw new NotFoundError(`Show with id "${id}" not found`);
        }

        const show: ShowDetailDTO = {
            // includeClubLocation: false — the /api/v1/shows/[id] route
            // spreads this DTO into its response and the OpenAPI ShowDetail
            // schema has no clubCity/clubState (nested club object instead).
            ...mapShowRowToDTO(row, {
                includeDescription: true,
                includeClubLocation: false,
            }),
            showPageUrl: row.showPageUrl,
        };
        return { show, clubId: row.club.id };
    } catch (error) {
        if (error instanceof NotFoundError) {
            throw error;
        }
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }
}
