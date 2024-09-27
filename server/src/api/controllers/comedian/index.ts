import * as comedianDal from "../../../database/dal/comedian.js"
import * as showComedianDal from "../../../database/dal/showComedian.js"
import { 
    CreateComedianDTO,
    CreateComedianOutput, 
    MergeComedianDTO, 
} from '../../dto/comedian.dto.js'
import { GetShowDetailsOutput } from "../../dto/show.dto.js"
import { ComedianInterface } from "../../../common/interfaces/comedian.interface.js"

export const createAll = async (comedians: CreateComedianDTO[]): Promise<CreateComedianOutput[]> => {
    const badComedians = await comedianDal.getBadComedians()

    var responses: CreateComedianOutput[] = []

    for (let i = 0; i < comedians.length; i++) {
        const comedian = comedians[i]
        if (badComedians.includes(comedian.name)) break;
        const output = await create(comedian)
        responses.push(output)
    }

    return responses
}

export const create = async (payload: CreateComedianDTO): Promise<CreateComedianOutput> => {
    return comedianDal.createComedian(payload)
}

export const getAllComedians = async (): Promise<ComedianInterface[]> => {
    return comedianDal.getAllComedians()
}

export const getById = async (id: number): Promise<ComedianInterface> => {
    return comedianDal.getComedianById(id)
}

export const getTrendingComedians = async (): Promise<ComedianInterface[]> => {
    return comedianDal.getTrendingComedians()
}

export const getAllShowsById = async (id: number): Promise<GetShowDetailsOutput[]> => {
    return showComedianDal.getAllShowsForComedian(id)
}

export const deleteById = async (id: number): Promise<boolean> => {
    return comedianDal.deleteComedianById(id)
}

export const merge = async (payload: MergeComedianDTO): Promise<boolean> => {
    const remainingId = payload.persistantId;
    const mergingIds = payload.mergedIds

    return true;
}