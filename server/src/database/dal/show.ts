import { CreateShowDTO, CreateShowOutput, GetFilteredShowsRequest, GetFilteredShowsResponse, GetShowByClubAndTimeDTO, GetShowDetailsOutput, GetShowIdOutput, ShowExistenceDTO, ShowScore } from "../../api/dto/show.dto.js"
import { DATABASE } from "../constants/database.js"
import { checkForExistence, deleteWithCondition, executeQuery, getAll, getAllWithCondition, getFirstWithCondition, upsertAndReplace } from "../util/queryUtil.js"
import { toShow } from "../../api/controllers/show/mapper.js"
import { ShowInterface } from "../../common/interfaces/show.interface.js"
import { GetSearchResultsOutput } from "../../api/dto/comedian.dto.js"

export const createShow = async (payload: CreateShowDTO): Promise<CreateShowOutput> => {
    return upsertAndReplace(DATABASE.SHOWS_TABLE,
        `(date_time, ticket_link, club_id) VALUES($1, $2, $3)`,
        `(club_id, date_time)`,
        `ticket_link=$2`,
        [payload.dateTime, payload.ticketLink, payload.clubId])
}

export const getShowByClubAndTime = async (payload: GetShowByClubAndTimeDTO): Promise<GetShowIdOutput> => {
    return getFirstWithCondition(DATABASE.SHOWS_TABLE,
        `club_id=$1 AND date_time=$2`,
        'id',
        [payload.clubId, payload.dateTime]
    )
}

export const checkIfShowExists = async (payload: ShowExistenceDTO): Promise<boolean> => {
    return checkForExistence(DATABASE.SHOWS_TABLE, "club_id=$1 AND date_time=$2", [payload.clubId, payload.dateTime])
}

export const getShowById = async (id: number): Promise<GetShowDetailsOutput> => {
    return getFirstWithCondition<GetShowDetailsOutput>(DATABASE.SHOWS_TABLE,
        `id=$1`,
        `id, club_id, date_time, ticket_link`,
        [id]
    )
}

export const getAllShows = async (): Promise<ShowInterface[]> => {
    return getAll<GetShowDetailsOutput>(DATABASE.SHOWS_TABLE)
        .then((queryResponse: GetShowDetailsOutput[]) => {
            return queryResponse.map((object: GetShowDetailsOutput) => toShow(object))
        })
}

export const getAllShowsForClubs = async (clubIds: number[]): Promise<ShowInterface[]> => {
    return getAllWithCondition<GetShowDetailsOutput>(DATABASE.SHOWS_TABLE, `club_id = ANY($1::int[])`, [clubIds])
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

export const getSearchResults = async (request: GetFilteredShowsRequest): Promise<GetSearchResultsOutput[]> => {
    const queryString = `
    SELECT show_id, comedian_id, c.name as comedian_name, instagram_account as instagram, date_time, ticket_link, address, base_url, cl.name as club_name, latitude, longitude
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
    return await executeQuery(queryString, [score.showId, score.score])

}