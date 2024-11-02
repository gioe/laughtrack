import {
    UpdateComedianRelationshipDTO,
    UpdateLineupItemDTO,
    CreateLineupItemDTO,
    GetLineupItemDTO,
} from "../../interfaces";
import { db } from "../../database";

export const addAll = async (items: CreateLineupItemDTO[]): Promise<null> => {
    return db.lineups.addAll(items);
};

export const update = async (
    payload: UpdateComedianRelationshipDTO,
): Promise<any[]> => {
    const shows = await db.lineups.findByComedianId(payload.child_id);

    if (shows && shows.length > 0) {
        const updateRecords = shows.map((item: GetLineupItemDTO) => {
            return {
                id: item.id,
                comedian_id: payload.parent_id,
            } as UpdateLineupItemDTO;
        });

        return db.lineups.updateLineups(updateRecords);
    }

    return [];
};
