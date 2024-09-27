import {
    CreateClubOutput,
    GetClubOutput
} from "../../api/dto/club.dto.js"
import { ClubInterface } from "../../common/interfaces/club.interface.js"
import {
    getAll,
    getFirstWithCondition,
    getAllWithCondition,
    executeQuery,
    upsertAndReplace,
    deleteWithCondition
} from "../util/queryUtil.js"
import { DATABASE } from "../constants/database.js"
import { readFile } from "../../api/util/storageUtil.js"
import { clubArrayFromJson, toClub } from "../../api/controllers/club/mapper.js"


export const getAllClubsFromFile = async (): Promise<ClubInterface[]> => {
    return readFile(process.env.CLUBS_FILE_NAME as string)
        .then((clubsJson: any) => clubArrayFromJson(clubsJson))
}

export const getAllClubs = async (): Promise<ClubInterface[]> => {
    return getAll<GetClubOutput>(DATABASE.CLUBS_TABLE)
        .then((queryResponse: GetClubOutput[]) => queryResponse.map((object: GetClubOutput) => toClub(object)))
}

export const getClubsInLocation = async (location: string): Promise<ClubInterface[]> => {
    return getAllWithCondition<GetClubOutput>(DATABASE.CLUBS_TABLE, `city=$1`, [location])
        .then((queryResponse: GetClubOutput[]) => queryResponse.map((object: GetClubOutput) => toClub(object)))
}

export const getClubById = async (id: number): Promise<ClubInterface> => {
    return getFirstWithCondition<GetClubOutput>(DATABASE.CLUBS_TABLE, `id=$1`, [id])
        .then((queryResponse: GetClubOutput) => toClub(queryResponse))
}

export const deleteClubById = async (id: number): Promise<boolean> => {
    return deleteWithCondition(DATABASE.CLUBS_TABLE, `id=$1`, [id])
}

export const createClub = async (payload: ClubInterface): Promise<CreateClubOutput> => {
    return upsertAndReplace(DATABASE.CLUBS_TABLE,
        `(name, base_url, schedule_page_url, timezone, scraping_config, city,
         address, latitude, longitude, image_name) VALUES($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)`,
        `(name)`,
        `base_url=$2, schedule_page_url=$3, timezone=$4, scraping_config=$5, city=$6, a
        ddress=$7, latitude=$8, longitude=$9, image_name=$10`,
        [payload.name, payload.baseUrl, payload.schedulePageUrl, payload.timezone,
        payload.scrapingConfig, payload.city, payload.address, payload.latitude, payload.longitude, payload.imageName])
}

export const getTrendingClubs = async (): Promise<ClubInterface[]> => {
    const queryString = `
    SELECT c.id, c.name, c.base_url as url, popularity_score
    FROM ${DATABASE.CLUBS_TABLE} s 
    ORDER BY popularity_score DESC LIMIT 5;
    `
    return await executeQuery<GetClubOutput>(queryString, [])
    .then((queryResponse: GetClubOutput[]) => queryResponse.map((object: GetClubOutput) => toClub(object)))

}

