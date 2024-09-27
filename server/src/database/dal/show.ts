import {
    CreateShowDTO, 
    CreateShowOutput, 
    GetFilteredShowsRequest,
    GetShowDetailsOutput,
    ShowScore,
    UpdateShowScoreDTO
} from "../../api/dto/show.dto.js"
import { DATABASE } from "../constants/database.js"
import {
    deleteWithCondition, 
    executeQuery,
    getAll, 
    getAllWithCondition, 
    getFirstWithCondition, 
    upsertAndReplace
} from "../util/queryUtil.js"
import { toShow } from "../../api/controllers/show/mapper.js"
import { ShowInterface } from "../../common/interfaces/show.interface.js"
import { GetSearchResultsOutput } from "../../api/dto/comedian.dto.js"

export const createShow = async (payload: ShowInterface): Promise<ShowInterface> => {
    return upsertAndReplace<GetShowDetailsOutput>(DATABASE.SHOWS_TABLE,
        `(date_time, ticket_link, club_id) VALUES($1, $2, $3)`,
        `(club_id, date_time)`,
        `ticket_link=$2`,
        [payload.dateTime, payload.ticketLink, payload.clubId])
        .then((response: GetShowDetailsOutput) => toShow(response))
}

export const getShowByClubAndTime = async (payload: GetShowDetailsOutput): Promise<ShowInterface> => {
    return getFirstWithCondition<GetShowDetailsOutput>(DATABASE.SHOWS_TABLE, `club_id=$1 AND date_time=$2`, [payload.club_id, payload.date_time])
    .then((response: GetShowDetailsOutput) => toShow(response))
}

export const getShowById = async (id: number): Promise<ShowInterface> => {
    return getFirstWithCondition<GetShowDetailsOutput>(DATABASE.SHOWS_TABLE, `id=$1`, [id])
    .then((response: GetShowDetailsOutput) => toShow(response))
}

export const getAllShows = async (): Promise<ShowInterface[]> => {
    return getAll<GetShowDetailsOutput>(DATABASE.SHOWS_TABLE)
        .then((queryResponse: GetShowDetailsOutput[]) => queryResponse.map((object: GetShowDetailsOutput) => toShow(object)))
}

export const getAllShowsForClubs = async (clubIds: number[]): Promise<ShowInterface[]> => {
    return getAllWithCondition<GetShowDetailsOutput>(DATABASE.SHOWS_TABLE, `club_id = ANY($1::int[])`, [clubIds])
        .then((queryResponse: GetShowDetailsOutput[]) => queryResponse.map((object: GetShowDetailsOutput) => toShow(object)))
}

export const deleteShowById = async (id: number): Promise<boolean> => {
    return deleteWithCondition(DATABASE.SHOWS_TABLE, `id=$1`, [id])
}

export const updateScores = async (values: UpdateShowScoreDTO[]): Promise<boolean[]> => {
    const queryString = `
    UPDATE ${DATABASE.SHOWS_TABLE}
    SET score=$2
    WHERE id=$1;
    `
    return executeQuery<boolean>(queryString, [])
}

export const getSearchResults = async (request: GetFilteredShowsRequest): Promise<GetSearchResultsOutput[]> => {
    const queryString = `
    SELECT show_id, comedian_id, c.name as comedian_name, instagram_account as instagram, 
    date_time, ticket_link, address, base_url, cl.name as club_name, latitude, longitude
    FROM ${DATABASE.SHOW_COMEDIANS_TABLE} cs 
    INNER JOIN ${DATABASE.COMEDIANS_TABLE} c ON c.id = cs.comedian_id 
    INNER JOIN ${DATABASE.SHOWS_TABLE} s ON cs.show_id = s.id 
    INNER JOIN ${DATABASE.CLUBS_TABLE} cl ON s.club_id = cl.id 
    WHERE cl.city = $1 AND s.date_time < $2 AND $3 < s.date_time
    `
    return await executeQuery<GetSearchResultsOutput>(queryString, [request.location, request.endDate, request.startDate])
}

export const updateScore = async (score: ShowScore) => {
    const queryString = `
    UPDATE ${DATABASE.SHOWS_TABLE}
    SET score=$2
    WHERE id=$1;
    `
}