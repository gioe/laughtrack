import { UpdateComedianRelationshipDTO } from "../../../common/models/interfaces/comedian.interface.js"
import { db } from '../../../database/index.js';

export const establishGroup = async (payload: UpdateComedianRelationshipDTO) => {
    return db.groups.addComedianGroup(payload);
}