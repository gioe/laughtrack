import * as showDal from "../../../database/dal/show.js"
import * as comedianDal from "../../../database/dal/comedian.js"
import * as showComedianDal from "../../../database/dal/showComedian.js"
import { CreateShowDTO, CreateShowOutput, GetShowDetailsOutput } from '../../dto/show.dto.js'
import { ShowInterface } from "../../interfaces/show.interface.js"
import { runTasks } from "../../../util/promiseUtil.js"


export const createAll = async(allShows: ShowInterface[]): Promise<CreateShowOutput[]> => {
    const tasks = allShows.map((show: ShowInterface) => {
        return create({
            club_id: show.clubId,
            date_time: show.dateTime,
            ticket_link: show.ticketLink,
            comedians: show.comedians
        })
    })
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

export const getAll = async (): Promise<GetShowDetailsOutput[]> => {
    return showDal.getAllShows()
}

export const deleteOldShows = async (): Promise<boolean[]> => {
    const oldShows = await showDal.getOldShows()
    const oldShowIds: number[] = oldShows.map(show => show.id);
    await showComedianDal.deleteAllShows(oldShowIds)

    const tasks = oldShowIds.map(id => showDal.deleteShowById(id))
    return runTasks(tasks);

}
