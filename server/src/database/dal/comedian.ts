import {
    ComedianExistenceDTO,
    ComedianPopularityData,
    CreateComedianDTO,
    CreateComedianOutput,
    GetComedianDetailsOutput,
    TrendingComedian
} from "../../api/dto/comedian.dto.js"
import { runTasks } from "../../common/util/promiseUtil.js"
import { checkForExistence, deleteWithCondition, executeQuery, getAll, getFirstWithCondition, upsertAndDoNothing } from "../util/queryUtil.js"
import { DATABASE } from "../constants/database.js"
import { readFile } from "../../api/util/storageUtil.js"
import { JSON_KEYS } from "../../common/constants/keys.js"

export const getBadComedians = async (): Promise<string[]> => {
    return readFile(process.env.INVALID_COMEDIANS_FILE_NAME as string)
        .then((json: any) => {
            return json[JSON_KEYS.names].map((object: any) => {
                return object
            })
        })
}

export const createAllComedians = async (clubDtos: CreateComedianDTO[]): Promise<CreateComedianOutput[]> => {
    const badComedians = await getBadComedians();

    const tasks = clubDtos.filter((clubDto: CreateComedianDTO) => !badComedians.includes(clubDto.name))
        .map(clubDto => createComedian(clubDto))

    return runTasks(tasks)
}

export const createComedian = async (payload: CreateComedianDTO): Promise<CreateComedianOutput> => {
    return upsertAndDoNothing(DATABASE.COMEDIANS_TABLE, `(name) VALUES($1)`, `(name)`, [payload.name]).then((response: CreateComedianOutput | unknown) => {
        if (response == undefined) {
            return getComedianByName(payload.name)
        }
        return response as CreateComedianOutput
    })
}

export const checkForComedianExistence = async (payload: ComedianExistenceDTO): Promise<boolean> => {
    return checkForExistence(DATABASE.COMEDIANS_TABLE, "name=$1", [payload.name])
}

export const getComedianById = async (id: number): Promise<GetComedianDetailsOutput> => {
    return getFirstWithCondition<GetComedianDetailsOutput>(DATABASE.COMEDIANS_TABLE, 
        `id=$1`, 
        `name, instagram_account`,
        [id])
}

export const getComedianByName = async (name: string): Promise<CreateComedianOutput> => {
    return getFirstWithCondition<CreateComedianOutput>(DATABASE.COMEDIANS_TABLE, 
        `name=$1`, 
        `id`,
        [name])
}

export const getAllComedians = async (): Promise<GetComedianDetailsOutput[]> => {
    return getAll<GetComedianDetailsOutput>(DATABASE.COMEDIANS_TABLE)
}

export const deleteComedianById = async (id: number): Promise<boolean> => {
    return deleteWithCondition(DATABASE.COMEDIANS_TABLE, `id=$1`, [id])
}

export const getTrendingComedians = async (): Promise<TrendingComedian[]> => {
    const queryString = `
    SELECT c.id, c.name, c.instagram_account as instagram, count (*) 
    FROM ${DATABASE.SHOW_COMEDIANS_TABLE} 
    sc INNER JOIN ${DATABASE.COMEDIANS_TABLE} c ON sc.comedian_id = c.id
    WHERE c.name != 'Special Guest'
    GROUP BY 1 ORDER BY count DESC LIMIT 10;
    `
    return await executeQuery<TrendingComedian>(queryString, [])
}

export const getPopularityData = async (ids: number[]): Promise<ComedianPopularityData[]> => {
    const queryString = `
    SELECT instagram_followers as instagramFollowers,
    tiktok_followers as tiktokFollowers
    FROM ${DATABASE.COMEDIANS_TABLE} WHERE id = ANY($1::int[])
    `
    return await executeQuery<ComedianPopularityData>(queryString, [ids])
}


