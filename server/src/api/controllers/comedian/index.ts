import { take } from "lodash"
import { flatten } from "../../../common/util/arrayUtil.js"
import { runTasks } from "../../../common/util/promiseUtil.js"
import * as comedianDal from "../../../database/dal/comedian.js"
import * as showComedianDal from "../../../database/dal/showComedian.js"
import { CreateComedianDTO, CreateComedianOutput, GetComedianDetailsOutput, MergeComedianDTO } from '../../dto/comedian.dto.js'
import { GetShowDetailsOutput } from "../../dto/show.dto.js"
import { ComedianInterface } from "../../../common/interfaces/comedian.interface.js"
import { toComedian } from "./mapper.js"

export const create = async(payload: CreateComedianDTO): Promise<CreateComedianOutput> => {
    return comedianDal.createComedian(payload)
}

export const getById = async (id: number): Promise<ComedianInterface> => {
    return comedianDal.getComedianById(id)
    .then((comedianDetails: GetComedianDetailsOutput) => toComedian(comedianDetails))
}

export const getAllShowsByIds = async (comedianIds: number[]): Promise<GetShowDetailsOutput[]> => {
    const tasks = comedianIds.map((id: number) => getAllShowsById(id))
    return runTasks(tasks).then((showArrays: GetShowDetailsOutput[][]) => flatten(showArrays))
}


export const getAllShowsById = async (id: number): Promise<GetShowDetailsOutput[]> => {
    const shows = showComedianDal.getAllShowsForComedian(id)
    return shows;
}

export const deleteAllComediansById = async(comedianIds: number[]): Promise<boolean> => {
    const tasks = comedianIds.map((id: number) => deleteById(id))
    return runTasks(tasks).then((responses: boolean[]) => true)
}

export const deleteById = async(id: number): Promise<boolean> => {
    return comedianDal.deleteComedianById(id)
}

export const getAll = async (): Promise<GetComedianDetailsOutput[]> => {
    return comedianDal.getAllComedians()
}

export const getAlComediansByIds = async (ids: number[]): Promise<ComedianInterface[]> => {
    const tasks = ids.map((id: number) => getById(id))
    return runTasks(tasks)
}

export const merge = async (payload: MergeComedianDTO): Promise<boolean> => {
    const remainingId = payload.persistantId;
    const mergingIds = payload.mergedIds

    return showComedianDal.deleteAllRelationshipsByComedians(mergingIds)
    .then(() => deleteAllComediansById(mergingIds))
    .then(() => getAllShowsByIds(mergingIds)) 
    .then((shows: GetShowDetailsOutput[]) => {
        const showIds = shows.map((show: GetShowDetailsOutput) => show.id)
        return showComedianDal.createShowComedianRelationshipsByIds(remainingId, [...new Set(showIds)])
    })
    .then(() => true)

}