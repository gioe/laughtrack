import { TagShowDTO, GetTagDTO, GetTagResponseDTO, TagInterface, TagComedianDTO, TagClubDTO } from '../../../common/models/interfaces/tag.interface.js';
import { toTagInterfaceArray } from '../../../common/util/domainModels/tag/mapper.js';
import { db } from '../../../database/index.js';

export const addShowTags = async (items: TagShowDTO[]): Promise<null> => {
    return db.tags.addAllShowTags(items);
}

export const addComedianTags = async (items: TagComedianDTO[]): Promise<null> => {
    return db.tags.addAllComedianTags(items);
}

export const addClubTags = async (items: TagClubDTO[]): Promise<null> => {
    return db.tags.addAllClubTags(items);
}

export const getAllByType = async (payload: GetTagDTO):  Promise<TagInterface[]>=> {
    return db.tags.getAllByType(payload).then((response: GetTagResponseDTO[] | null) => response ? toTagInterfaceArray(response) : [])
}
