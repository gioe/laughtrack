import { DATABASE } from "../constants/database.js"
import { 
    create,
    deleteWithCondition,
    executeQuery
} from "../util/queryUtil.js"
import { CreateShowComedianDTO, CreateShowComedianOutput } from "../../api/dto/showComedian.dto.js"
import { CreateShowOutput, GetShowDetailsOutput } from "../../api/dto/show.dto.js"
import { CreateComedianOutput, GetComedianDetailsOutput } from "../../api/dto/comedian.dto.js"
import { runTasks } from "../../common/util/promiseUtil.js"

export const createShowComedianRelationshipsByIds = async (comedianId: number, showIds: number[]): Promise<CreateShowComedianOutput[]> => {
    const tasks = showIds.map(showId => {
        return createShowComedianRelationship({
            showId,
            comedianId
        })
    })
    return runTasks(tasks);
}

export const createShowComedianRelationships = async (comedians: CreateComedianOutput[], show: CreateShowOutput): Promise<CreateShowComedianOutput[]> => {
    const tasks = comedians.map(comedian => {
        return createShowComedianRelationship({
            showId: show.id,
            comedianId: comedian.id
        })
    })
    return runTasks(tasks);
}

export const createShowComedianRelationship = async (payload: CreateShowComedianDTO): Promise<CreateShowComedianOutput> => {
    return create(DATABASE.SHOW_COMEDIANS_TABLE, 
        `(show_id, comedian_id) VALUES($1, $2)`,
        [payload.showId, payload.comedianId])
}

export const getAllShowsForComedian = async (comedianId: number): Promise<GetShowDetailsOutput[]> => {
    const queryString = `
    SELECT * FROM ${DATABASE.SHOW_COMEDIANS_TABLE} cs INNER JOIN ${DATABASE.SHOWS_TABLE} s ON s.id = cs.show_id WHERE cs.comedian_id = $1;
    `
    const shows  = await executeQuery<GetShowDetailsOutput>(queryString, [comedianId])
    return shows
}

export const getAllComediansInShow = async (showId: number): Promise<GetComedianDetailsOutput[]> => {
    const queryString = `
    SELECT * FROM ${DATABASE.SHOW_COMEDIANS_TABLE} cs INNER JOIN ${DATABASE.COMEDIANS_TABLE} c ON c.id = cs.comedian_id WHERE cs.show_id = $1;
    `
    return await executeQuery<GetComedianDetailsOutput>(queryString, [showId])
}

export const deleteAllRelationshipsByShows = async (showIds: number[]): Promise<boolean> => {
    return deleteWithCondition(DATABASE.SHOW_COMEDIANS_TABLE, `show_id = ANY($1::int[])`, [showIds])
}

export const deleteAllRelationshipsByComedians = async (comedianIds: number[]): Promise<boolean> => {
    return deleteWithCondition(DATABASE.SHOW_COMEDIANS_TABLE, `comedian_id = ANY($1::int[])`, [comedianIds])
}


