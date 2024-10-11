import { ShowInterface, GetShowResponseDTO } from "../../../models/interfaces/show.interface.js"
import { GetDateDTO } from "../../../models/interfaces/comedian.interface.js"
import { toLineup } from "../lineupItem/mapper.js"

export const toDates = (payload: GetDateDTO[] | GetShowResponseDTO[]): ShowInterface[] => {
    return payload.map((show: GetDateDTO | GetShowResponseDTO) => toShowInterface(show));
}

export const toShowInterface = (payload: GetShowResponseDTO | GetDateDTO): ShowInterface => {
    return {
        id: payload.id,
        dateTime: payload.date_time,
        ticketLink: payload.ticket_link,
        clubId: payload.club_id,
        clubName: payload.club_name,
        lineup: toLineup(payload.lineup),
        popularityScore: payload.popularity_score
    }
}