import { UpdateComedianRelationshipDTO, UpdateLineupItemDTO } from "../../../common/models/interfaces/comedian.interface.js";
import { CreateLineupItemDTO, GetLineupItemDTO } from "../../../common/models/interfaces/lineupItem.interface.js";
import { db } from '../../../database/index.js';

export const addAll = async (items: CreateLineupItemDTO[]): Promise<null> => {
    return db.lineups.addAll(items);
}

export const update = async (payload: UpdateComedianRelationshipDTO): Promise<any[]> => {
    const shows = await db.lineups.findByComedianId(payload.child_id)

    if (shows && shows.length > 0) {
        const updateRecords = shows.map((item: GetLineupItemDTO) => {
            return {
                id: item.id,
                comedian_id: payload.parent_id
            } as UpdateLineupItemDTO;
        })

        return db.lineups.updateLineups(updateRecords)
    } 


    return []
}


