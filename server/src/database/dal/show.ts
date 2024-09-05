import {  CreateShowDTO, CreateShowOutput, GetShowByClubAndTimeDTO, GetShowDetailsOutput, GetShowIdOutput,  ShowExistenceDTO } from "../../api/dto/show.dto.js"
import { DATABASE } from "../../constants/database.js"
import { runTasks } from "../../util/promiseUtil.js"
import { checkForExistence, deleteWithCondition, getAll, getAllWithCondition, getFirstWithCondition, upsert } from "../../util/queryUtil.js"

export const createAllShows = async (clubDtos: CreateShowDTO[]): Promise<CreateShowOutput[]> => {
    const tasks = clubDtos.map(clubDto => createShow(clubDto))
    return runTasks(tasks)
}

export const createShow = async (payload: CreateShowDTO): Promise<CreateShowOutput> => {
    return upsert(DATABASE.SHOWS_TABLE, 
        `(date_time, ticket_link, club_id) VALUES($1, $2, $3)`,
        `(club_id, date_time)`,
        `ticket_link=$2`,
        [payload.date_time, payload.ticket_link, payload.club_id])
}

export const getShowByClubAndTime = async (payload: GetShowByClubAndTimeDTO): Promise<GetShowIdOutput> => {
    return getFirstWithCondition(DATABASE.SHOWS_TABLE, `club_id=$1 AND date_time=$2`, [payload.club_id, payload.date_time])
}

export const checkIfShowExists = async (payload: ShowExistenceDTO): Promise<boolean> => {
    return checkForExistence(DATABASE.SHOWS_TABLE, "club_id=$1 AND date_time=$2", [payload.club_id, payload.date_time])
}

export const getShowById = async (id: number): Promise<GetShowDetailsOutput> => {
    return getFirstWithCondition<GetShowDetailsOutput>(DATABASE.SHOWS_TABLE, `id=$1`, [id])
}

export const getAllShows = async (): Promise<GetShowDetailsOutput[]>  => {
    return getAll<GetShowDetailsOutput>(DATABASE.SHOWS_TABLE)
}

export const deleteShowById = async (id: number): Promise<boolean> => {
    return deleteWithCondition(DATABASE.SHOWS_TABLE, `id=$1`, [id])
}

export const getOldShows = async (): Promise<GetShowIdOutput[]> => {
    return getAllWithCondition<GetShowIdOutput>(DATABASE.SHOWS_TABLE, `date_time < now()`)
}

export const deleteOldShows = async (): Promise<boolean> => {
    return deleteWithCondition(DATABASE.SHOWS_TABLE, `date_time < now()`)
}
