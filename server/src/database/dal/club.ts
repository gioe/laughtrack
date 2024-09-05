import { ClubExistenceDTO, CreateClubDTO, CreateClubOutput, GetClubOutput } from "../../api/dto/club.dto.js"
import { ClubInterface } from "../../api/interfaces/club.interface.js"
import { runTasks } from "../../util/promiseUtil.js"
import { checkForExistence, deleteWithCondition, getAll, getFirstWithCondition, create, upsert } from "../../util/queryUtil.js"
import { DATABASE } from "../../constants/database.js"

export const createAllClubs = async (clubs: ClubInterface[]): Promise<CreateClubOutput[]> => {
    const tasks = clubs.map(club => createClub({
        name: club.name,
        base_url: club.baseUrl,
        schedule_page_url: club.schedulePageUrl,
        timezone: club.timezone,
        scraping_config: club.scrapingConfig
    }))
    return runTasks(tasks)
}

export const createClub = async (payload: CreateClubDTO): Promise<CreateClubOutput> => {
    return upsert(DATABASE.CLUBS_TABLE, 
        `(name, base_url, schedule_page_url, timezone, scraping_config) VALUES($1, $2, $3, $4, $5)`,
        `(name)`,
        `base_url=$2, schedule_page_url=$3, timezone=$4, scraping_config=$5`,
        [payload.name, payload.base_url, payload.schedule_page_url, payload.timezone, payload.scraping_config])
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
    return getAll<ClubInterface>(DATABASE.CLUBS_TABLE)
}

export const deleteClubById = async (id: number): Promise<boolean> => {
    return deleteWithCondition(DATABASE.CLUBS_TABLE, `id=$1`, [id])
}
