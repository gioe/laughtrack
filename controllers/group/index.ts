import { UpdateComedianRelationshipDTO } from "../../interfaces";
import { db } from '../../database';

export const establishGroup = async (payload: UpdateComedianRelationshipDTO) => {
    return db.groups.addComedianGroup(payload);
}