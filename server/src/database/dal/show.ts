import {  CreateShowDTO, CreateShowOutput, GetShowByClubAndTimeDTO, GetShowDetailsOutput, GetShowIdOutput,  ShowExistenceDTO } from "../../api/dto/show.dto.js"
import { DATABASE } from "../constants/database.js"
import { runTasks } from "../../common/util/promiseUtil.js"
import { checkForExistence, deleteWithCondition, getAll, getAllWithCondition, getFirstWithCondition, upsert } from "../util/queryUtil.js"
import { toShow } from "../../api/controllers/show/mapper.js"
import { ShowInterface } from "../../common/interfaces/show.interface.js"

export const createAllShows = async (clubDtos: CreateShowDTO[]): Promise<CreateShowOutput[]> => {
    const tasks = clubDtos.map(clubDto => createShow(clubDto))
    return runTasks(tasks)
}

export const createShow = async (payload: CreateShowDTO): Promise<CreateShowOutput> => {
    return upsert(DATABASE.SHOWS_TABLE, 
        `(date_time, ticket_link, club_id) VALUES($1, $2, $3)`,
        `(club_id, date_time)`,
        `ticket_link=$2`,
        [payload.dateTime, payload.ticketLink, payload.clubId])
}

export const getShowByClubAndTime = async (payload: GetShowByClubAndTimeDTO): Promise<GetShowIdOutput> => {
    return getFirstWithCondition(DATABASE.SHOWS_TABLE, `club_id=$1 AND date_time=$2`, [payload.clubId, payload.dateTime])
}

export const checkIfShowExists = async (payload: ShowExistenceDTO): Promise<boolean> => {
    return checkForExistence(DATABASE.SHOWS_TABLE, "club_id=$1 AND date_time=$2", [payload.clubId, payload.dateTime])
}

export const getShowById = async (id: number): Promise<GetShowDetailsOutput> => {
    return getFirstWithCondition<GetShowDetailsOutput>(DATABASE.SHOWS_TABLE, `id=$1`, [id])
}

export const getAllShows = async (): Promise<ShowInterface[]>  => {
    return getAll<GetShowDetailsOutput>(DATABASE.SHOWS_TABLE)
    .then((queryResponse: GetShowDetailsOutput[]) => {
        return queryResponse.map((object: GetShowDetailsOutput) => toShow(object))
    })
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
