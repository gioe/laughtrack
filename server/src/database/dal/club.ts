import { ClubExistenceDTO, CreateClubDTO, CreateClubOutput, GetClubOutput } from "../../api/dto/club.dto.js"
import { ClubInterface } from "../../common/interfaces/club.interface.js"
import { runTasks } from "../../common/util/promiseUtil.js"
import { checkForExistence, deleteWithCondition, getAll, getFirstWithCondition, create, upsert, getAllWithCondition } from "../util/queryUtil.js"
import { DATABASE } from "../constants/database.js"
import { readFile } from "../../api/util/storageUtil.js"
import { JSON_KEYS } from "../../common/constants/keys.js"
import { toClub } from "../../api/controllers/club/mapper.js"

export const getAllClubsFromFile = async (): Promise<ClubInterface[]> => {    
    return readFile(process.env.CLUBS_FILE_NAME as string)
        .then((clubsJson: any) => clubArrayFromJson(clubsJson))
}

export const createAllClubs = async (clubs: ClubInterface[]): Promise<CreateClubOutput[]> => {
    const tasks = clubs.map(club => createClub(club))
    return runTasks(tasks)
}

export const createClub = async (payload: ClubInterface): Promise<CreateClubOutput> => {
    return upsert(DATABASE.CLUBS_TABLE, 
        `(name, base_url, schedule_page_url, timezone, scraping_config, city, address) VALUES($1, $2, $3, $4, $5, $6, $7)`,
        `(name)`,
        `base_url=$2, schedule_page_url=$3, timezone=$4, scraping_config=$5, city=$6, address=$7`,
        [payload.name, payload.baseUrl, payload.schedulePageUrl, payload.timezone, payload.scrapingConfig, payload.city, payload.address])
}

export const getClubByName = async (name: string): Promise<ClubInterface> => {
    return getFirstWithCondition<ClubInterface>(DATABASE.CLUBS_TABLE, `name=$1`, [name])
}

export const checkIfClubExists = async (payload: ClubExistenceDTO): Promise<boolean> => {
    return checkForExistence(DATABASE.CLUBS_TABLE, "name=$1", [payload.name])
}

export const getClubById = async (id: number): Promise<GetClubOutput> => {
    return getFirstWithCondition<GetClubOutput>(DATABASE.CLUBS_TABLE, `id=$1`, [id])
}

export const getAllClubs = async (): Promise<ClubInterface[]> => {
    return getAll<GetClubOutput>(DATABASE.CLUBS_TABLE)
    .then((queryResponse: GetClubOutput[]) => {
        return queryResponse.map((object: GetClubOutput) => toClub(object))
    })
}

export const deleteClubById = async (id: number): Promise<boolean> => {
    return deleteWithCondition(DATABASE.CLUBS_TABLE, `id=$1`, [id])
}

export const getClubsInLocation = async (location: string):  Promise<ClubInterface[]> => {
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