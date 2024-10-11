import { ShowInterface, GetShowResponseDTO } from "../../../models/interfaces/show.interface.js"
import { GetDateDTO } from "../../../models/interfaces/comedian.interface.js"
import { toLineupItemArray } from "../lineupItem/mapper.js"

export const toDates = (payload: GetDateDTO[] | GetShowResponseDTO[] | undefined, filter?: string, sort?: string): ShowInterface[] => {
    if (payload == undefined) return []
    return payload.map((show: GetDateDTO | GetShowResponseDTO) => toShowInterface(show, filter));
}

export const toShowInterface = (payload: GetShowResponseDTO | GetDateDTO, filter?: string): ShowInterface => {
    return {
        id: payload.id,
        dateTime: payload.date_time,
        ticketLink: payload.ticket_link,
        clubId: payload.club_id,
        clubName: payload.club_name,
        lineup: toLineupItemArray(payload.lineup, filter),
        popularityScore: payload.popularity_score
    }
}