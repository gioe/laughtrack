import { ComedianExistenceDTO, CreateComedianDTO, CreateComedianOutput, GetComedianDetailsOutput, TrendingComedian } from "../../api/dto/comedian.dto.js"
import { runTasks } from "../../common/util/promiseUtil.js"
import { checkForExistence, deleteWithCondition, executeQuery, getAll, getFirstWithCondition, upsert } from "../util/queryUtil.js"
import { DATABASE } from "../constants/database.js"

export const createAllComedians = async (clubDtos: CreateComedianDTO[]): Promise<CreateComedianOutput[]> => {
    const tasks = clubDtos.map(clubDto => createComedian(clubDto))
    return runTasks(tasks)
}

export const createComedian = async (payload: CreateComedianDTO): Promise<CreateComedianOutput> => {
    return upsert(DATABASE.COMEDIANS_TABLE, 
        `(name, instagram) VALUES($1, $2)`,
        `(name)`,
        `instagram=$2`,
        [payload.name, payload.instagram])
}

export const checkForComedianExistence = async (payload: ComedianExistenceDTO): Promise<boolean> => {
    return checkForExistence(DATABASE.COMEDIANS_TABLE, "name=$1", [payload.name])
}

export const getComedianById = async (id: number): Promise<GetComedianDetailsOutput> => {
    return getFirstWithCondition<GetComedianDetailsOutput>(DATABASE.COMEDIANS_TABLE, `id=$1`, [id])
}

export const getAllComedians = async (): Promise<GetComedianDetailsOutput[]> => {
    return getAll<GetComedianDetailsOutput>(DATABASE.COMEDIANS_TABLE)
}

export const deleteComedianById = async (id: number): Promise<boolean> => {
    return deleteWithCondition(DATABASE.COMEDIANS_TABLE, `id=$1`, [id])
}

export const getTrendingComedians = async (): Promise<TrendingComedian[]> => {
    const queryString = `
    SELECT c.id, c.name, c.instagram, count (*) FROM ${DATABASE.SHOW_COMEDIANS_TABLE} 
    sc INNER JOIN ${DATABASE.COMEDIANS_TABLE} c ON sc.comedian_id = c.id GROUP BY 1 ORDER BY count DESC LIMIT 10;
    `
    return await executeQuery<TrendingComedian>(queryString, [])
}

