import { GetTagDTO, GetTagResponseDTO, TagInterface } from '../../../common/models/interfaces/tag.interface.js';
import { toTagInterfaceArray } from '../../../common/util/domainModels/tag/mapper.js';
import { db } from '../../../database/index.js';

export const getAllByType = async (payload: GetTagDTO):  Promise<TagInterface[]>=> {
    return db.tags.getAllByType(payload).then((response: GetTagResponseDTO[] | null) => response ? toTagInterfaceArray(response) : [])
}
