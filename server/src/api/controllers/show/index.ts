import * as showDal from "../../../database/dal/show.js"
import * as comedianDal from "../../../database/dal/comedian.js"
import * as showComedianDal from "../../../database/dal/showComedian.js"
import { CreateShowDTO, CreateShowOutput, GetShowDetailsOutput } from '../../dto/show.dto.js'
import { ShowInterface } from "../../../common/interfaces/show.interface.js"
import { runTasks } from "../../../common/util/promiseUtil.js"

export const createAll = async(allShows: ShowInterface[]): Promise<CreateShowOutput[]> => {
    const tasks = allShows.map((show: ShowInterface) =>  create(show))
    return runTasks(tasks);
}

export const create = async(payload: CreateShowDTO): Promise<CreateShowOutput> => {
    const show = await showDal.createShow(payload)
    const comedians = await comedianDal.createAllComedians(payload.comedians)
    await showComedianDal.createShowComedianRelationships(comedians, show)
    return show;
}

export const getById = async (id: number): Promise<GetShowDetailsOutput> => {
    return showDal.getShowById(id)
}

export const deleteById = async(id: number): Promise<boolean> => {
    return showDal.deleteShowById(id)
}

export const getAll = async (): Promise<ShowInterface[]> => {
    return showDal.getAllShows()
}

export const deleteOldShows = async (): Promise<void> => {
    const oldShows = await showDal.getOldShows()

    if (oldShows !== undefined && oldShows.length > 0) {
        const oldShowIds: number[] = oldShows.map(show => show.id);
        await showComedianDal.deleteAllRelationshipsByShows(oldShowIds)
        const tasks = oldShowIds.map(id => showDal.deleteShowById(id))
        runTasks(tasks);
    }
}
