import { 
    ClubExistenceDTO, 
    CreateClubOutput, 
    GetClubOutput, 
    TrendingClub 
} from "../../api/dto/club.dto.js"
import { ClubInterface } from "../../common/interfaces/club.interface.js"
import { 
    checkForExistence, 
    deleteWithCondition, 
    getAll,
    getFirstWithCondition, 
    getAllWithCondition, 
    executeQuery, 
    upsertAndReplace
} from "../util/queryUtil.js"
import { DATABASE } from "../constants/database.js"
import { readFile } from "../../api/util/storageUtil.js"
import { JSON_KEYS } from "../../common/constants/keys.js"
import { toClub } from "../../api/controllers/club/mapper.js"

export const getAllClubsFromFile = async (): Promise<ClubInterface[]> => {
    return readFile(process.env.CLUBS_FILE_NAME as string)
        .then((clubsJson: any) => clubArrayFromJson(clubsJson))
}

export const createClub = async (payload: ClubInterface): Promise<CreateClubOutput> => {
    return upsertAndReplace(DATABASE.CLUBS_TABLE,
        `(name, base_url, schedule_page_url, timezone, scraping_config, city, address, latitude, longitude) VALUES($1, $2, $3, $4, $5, $6, $7, $8, $9)`,
        `(name)`,
        `base_url=$2, schedule_page_url=$3, timezone=$4, scraping_config=$5, city=$6, address=$7, latitude=$8, longitude=$9`,
        [payload.name, payload.baseUrl, payload.schedulePageUrl, payload.timezone, payload.scrapingConfig, payload.city, payload.address, payload.latitude, payload.longitude])
}

export const getClubByName = async (name: string): Promise<ClubInterface> => {
    return getFirstWithCondition<ClubInterface>(DATABASE.CLUBS_TABLE, 
        `name=$1`, 
        `id, name, baseUrl, schedulePageUrl, timezone, scrapingConfig, city, address, latitude, longitude`,
        [name])
}

export const checkIfClubExists = async (payload: ClubExistenceDTO): Promise<boolean> => {
    return checkForExistence(DATABASE.CLUBS_TABLE, "name=$1", [payload.name])
}

export const getClubById = async (id: number): Promise<GetClubOutput> => {
    return getFirstWithCondition<GetClubOutput>(DATABASE.CLUBS_TABLE, 
        `id=$1`, 
        `id, name, baseUrl, schedulePageUrl, timezone, scrapingConfig, city, address, latitude, longitude`,
        [id])
}

export const getAllClubs = async (): Promise<ClubInterface[]> => {
    return getAll<GetClubOutput>(DATABASE.CLUBS_TABLE)
        .then((queryResponse: GetClubOutput[]) => {
            return queryResponse.map((object: GetClubOutput) => toClub(object))
        })
}

export const getTrendingClubs = async (): Promise<TrendingClub[]> => {
    const queryString = `
    SELECT c.id, c.name, c.base_url as url, count (*) FROM ${DATABASE.SHOWS_TABLE} s INNER JOIN ${DATABASE.CLUBS_TABLE} c ON s.club_id = c.id 
    GROUP BY 1 ORDER BY count DESC LIMIT 5;
    `
    return await executeQuery<TrendingClub>(queryString, [])
}

export const deleteClubById = async (id: number): Promise<boolean> => {
    return deleteWithCondition(DATABASE.CLUBS_TABLE, `id=$1`, [id])
}

export const getClubsInLocation = async (location: string): Promise<ClubInterface[]> => {
    return getAllWithCondition<GetClubOutput>(DATABASE.CLUBS_TABLE, `city=$1`, [location])
        .then((queryResponse: GetClubOutput[]) => queryResponse.map((object: GetClubOutput) => toClub(object)))
}

const clubArrayFromJson = (json: any) => {
    var clubArray: ClubInterface[] = []

    for (let index = 0; index < json[JSON_KEYS.clubs].length - 1; index++) {
        const currentItem = json[JSON_KEYS.clubs][index];
        const currenItemClubs = currentItem[JSON_KEYS.clubDetails];

        currenItemClubs.forEach((club: any) => {
            const clubObject = {
                ...club,
                scrapingConfig: currentItem[JSON_KEYS.scrapingConfig]
            }
            clubArray.push(clubObject)
        })
    }

    return clubArray;

}