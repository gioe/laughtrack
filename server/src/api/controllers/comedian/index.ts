import * as comedianDal from "../../../database/dal/comedian.js"
import * as showComedianDal from "../../../database/dal/showComedian.js"
import * as showComedianController from "../showComedian/index.js"
import { 
    CreateComedianDTO,
    CreateComedianOutput, 
    GetComedianDetailsOutput, 
    MergeComedianDTO, 
    TrendingComedian 
} from '../../dto/comedian.dto.js'
import { GetShowDetailsOutput } from "../../dto/show.dto.js"
import { ComedianInterface } from "../../../common/interfaces/comedian.interface.js"
import { toComedian } from "./mapper.js"
import { flatten } from "../../../common/util/arrayUtil.js"
import { runTasks } from "../../../common/util/promiseUtil.js"
import { processPopularityData } from "../../util/scoringUtil.js"

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

export const getById = async (id: number): Promise<ComedianInterface> => {
    return comedianDal.getComedianById(id)
        .then((comedianDetails: GetComedianDetailsOutput) => toComedian(comedianDetails))
}

export const getTrendingComedians = async (): Promise<TrendingComedian[]> => {
    return comedianDal.getTrendingComedians()
}

export const getAllShowsByIds = async (comedianIds: number[]): Promise<GetShowDetailsOutput[]> => {
    const tasks = comedianIds.map((id: number) => getAllShowsById(id))
    return runTasks(tasks).then((showArrays: GetShowDetailsOutput[][]) => flatten(showArrays))
}

export const getAllShowsById = async (id: number): Promise<GetShowDetailsOutput[]> => {
    const shows = showComedianDal.getAllShowsForComedian(id)
    return shows;
}

export const deleteAllComediansById = async (comedianIds: number[]): Promise<boolean> => {
    const tasks = comedianIds.map((id: number) => deleteById(id))
    return runTasks(tasks).then((responses: boolean[]) => true)
}

export const deleteById = async (id: number): Promise<boolean> => {
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
        .then((shows: GetShowDetailsOutput[]) => showComedianController.createRelationshipForShows(remainingId, shows))
        .then(() => true)

}

export const getPopularityScore = async (comedians: ComedianInterface[]): Promise<number> => {
    const ids = comedians.map((comedian: ComedianInterface) => comedian.id);
    const data = await comedianDal.getPopularityData(ids)
    return processPopularityData(data)
}


