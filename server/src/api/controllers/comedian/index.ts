import * as comedianDal from "../../../database/dal/comedian.js"
import * as showComedianDal from "../../../database/dal/showComedian.js"
import { CreateComedianDTO, CreateComedianOutput, GetComedianDetailsOutput, GetComedianShowsOutput } from '../../dto/comedian.dto.js'

export const create = async(payload: CreateComedianDTO): Promise<CreateComedianOutput> => {
    return comedianDal.createComedian(payload)
}

export const getById = async (id: number): Promise<GetComedianDetailsOutput> => {
    return comedianDal.getComedianById(id)
}

export const getAllShowsById = async (id: number): Promise<GetComedianShowsOutput> => {
    const comedian = await comedianDal.getComedianById(id);
    return showComedianDal.getAllShowsForComedian(id, comedian.name)
}

export const deleteById = async(id: number): Promise<boolean> => {
    return comedianDal.deleteComedianById(id)
}

export const getAll = async (): Promise<GetComedianDetailsOutput[]> => {
    return comedianDal.getAllComedians()
}
