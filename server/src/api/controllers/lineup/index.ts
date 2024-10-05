import { CreateLineupItemDTO } from "../../../common/interfaces/data/lineupItem.interface.js";
import { db } from '../../../database/index.js';

export const addAll = async (items: CreateLineupItemDTO[]): Promise<null> => {
    return db.lineups.addAll(items);
}
