import {
    ComedianPopularityData,
    CreateComedianDTO,
    CreateComedianOutput,
    GetComedianDetailsOutput,
    TrendingComedian
} from "../../api/dto/comedian.dto.js"
import { deleteWithCondition, executeQuery, getAll, getFirstWithCondition, upsertAndDoNothing } from "../util/queryUtil.js"
import { DATABASE } from "../constants/database.js"
import { readFile } from "../../api/util/storageUtil.js"
import { JSON_KEYS } from "../../common/constants/keys.js"
import { toComedian } from "../../api/controllers/comedian/mapper.js"
import { ComedianInterface } from "../../common/interfaces/comedian.interface.js"

export const getBadComedians = async (): Promise<string[]> => {
    return readFile(process.env.INVALID_COMEDIANS_FILE_NAME as string)
        .then((json: any) => {
            return json[JSON_KEYS.names].map((object: any) => {
                return object
            })
        })
}

export const createComedian = async (payload: CreateComedianDTO): Promise<CreateComedianOutput> => {
    return upsertAndDoNothing(DATABASE.COMEDIANS_TABLE, `(name) VALUES($1)`, `(name)`, [payload.name])
    .then((response: CreateComedianOutput | unknown) => {
        if (response == undefined) {
            return getComedianByName(payload.name)
        }
        return response as CreateComedianOutput
    })
}


export const getComedianById = async (id: number): Promise<ComedianInterface> => {
    return getFirstWithCondition<GetComedianDetailsOutput>(DATABASE.COMEDIANS_TABLE, `id=$1`, [id])
    .then((queryResponse: GetComedianDetailsOutput) => toComedian(queryResponse))
}

export const getComedianByName = async (name: string): Promise<ComedianInterface> => {
    return getFirstWithCondition<GetComedianDetailsOutput>(DATABASE.COMEDIANS_TABLE, `name=$1`, [name])
    .then((queryResponse: GetComedianDetailsOutput) => toComedian(queryResponse))
}

export const getAllComedians = async (): Promise<ComedianInterface[]> => {
    return getAll<GetComedianDetailsOutput>(DATABASE.COMEDIANS_TABLE)
    .then((response: GetComedianDetailsOutput[]) => response.map((object: GetComedianDetailsOutput) => toComedian(object)))
}

export const deleteComedianById = async (id: number): Promise<boolean> => {
    return deleteWithCondition(DATABASE.COMEDIANS_TABLE, `id=$1`, [id])
}

export const getTrendingComedians = async (): Promise<TrendingComedian[]> => {
    const queryString = `
    SELECT c.id, c.name, c.instagram_account as instagram, count (*) 
    FROM ${DATABASE.SHOW_COMEDIANS_TABLE} 
    sc INNER JOIN ${DATABASE.COMEDIANS_TABLE} c ON sc.comedian_id = c.id
    WHERE c.is_pseudonym == false
    GROUP BY 1 ORDER BY count DESC LIMIT 10;
    `
    return await executeQuery<TrendingComedian>(queryString)
}

export const getPopularityData = async (ids: number[]): Promise<ComedianPopularityData[]> => {
    const queryString = `
    SELECT instagram_followers as instagramFollowers,
    tiktok_followers as tiktokFollowers
    FROM ${DATABASE.COMEDIANS_TABLE} WHERE id = ANY($1::int[])
    `
    return await executeQuery<ComedianPopularityData>(queryString, [ids])
}


