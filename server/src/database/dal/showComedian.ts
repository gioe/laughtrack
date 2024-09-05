import { DATABASE } from "../../constants/database.js"
import { 
    create,
    executeQuery
} from "../../util/queryUtil.js"
import { CreateShowComedianDTO, CreateShowComedianOutput } from "../../api/dto/showComedian.dto.js"
import { CreateShowOutput, GetShowDetailsOutput } from "../../api/dto/show.dto.js"
import { CreateComedianOutput, GetComedianDetailsOutput, GetComedianShowsOutput } from "../../api/dto/comedian.dto.js"
import { runTasks } from "../../util/promiseUtil.js"

export const createShowComedianRelationships = async (comedians: CreateComedianOutput[], show: CreateShowOutput): Promise<CreateShowComedianOutput[]> => {
    const tasks = comedians.map(comedian => {
        return createShowComedianRelationship({
            show_id: show.id,
            comedian_id: comedian.id
        })
    })
    return runTasks(tasks);
}

export const createShowComedianRelationship = async (payload: CreateShowComedianDTO): Promise<CreateShowComedianOutput> => {
    return create(DATABASE.SHOW_COMEDIANS_TABLE, 
        `(show_id, comedian_id) VALUES($1, $2)`,
        [payload.show_id, payload.comedian_id])
}

export const getAllShowsForComedian = async (comedianId: number, comedianName: string): Promise<GetComedianShowsOutput> => {
    const queryString = `
    SELECT * FROM ${DATABASE.SHOW_COMEDIANS_TABLE} cs INNER JOIN ${DATABASE.SHOWS_TABLE} s ON s.id = cs.show_id WHERE cs.comedian_id = $1;
    `
    const shows  = await executeQuery<GetShowDetailsOutput>(queryString, [comedianId])

    return {
        name: comedianName,
        count: shows.length,
        shows
    }
}

export const getAllComediansInShow = async (showId: number): Promise<GetComedianDetailsOutput[]> => {
    const queryString = `
    SELECT * FROM ${DATABASE.SHOW_COMEDIANS_TABLE} cs INNER JOIN ${DATABASE.COMEDIANS_TABLE} c ON c.id = cs.comedian_id WHERE cs.show_id = $1;
    `
    return await executeQuery<GetComedianDetailsOutput>(queryString, [showId])
}
