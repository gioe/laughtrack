import { TagShowDTO, GetTagDTO, GetTagResponseDTO, TagInterface, TagComedianDTO, TagClubDTO } from '../../interfaces';
import { toTagInterfaceArray } from '../../util/domainModels/tag/mapper';
import { db } from '../../database';

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
