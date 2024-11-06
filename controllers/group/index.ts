import { UpdateComedianRelationshipDTO } from "../../objects/interfaces";
import { getDB } from "../../database";

const { db } = getDB();

export const establishGroup = async (
    payload: UpdateComedianRelationshipDTO,
) => {
    return db.groups.addComedianGroup(payload);
};
