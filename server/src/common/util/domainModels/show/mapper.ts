import { ShowInterface, GetShowResponseDTO } from "../../../models/interfaces/show.interface.js"
import { GetDateDTO } from "../../../models/interfaces/comedian.interface.js"
import { toLineup } from "../lineupItem/mapper.js"
import { LineupItem } from "../../../models/interfaces/lineupItem.interface.js";

export const toDates = (payload: GetDateDTO[] | GetShowResponseDTO[]): ShowInterface[] => {
    return payload.map((show: GetDateDTO | GetShowResponseDTO) => toShowInterface(show));
}

export const toShowInterface = (payload: GetShowResponseDTO | GetDateDTO): ShowInterface => {
    return {
        id: payload.id,
        name: payload.name,
        dateTime: payload.date_time,
        ticketLink: payload.ticket_link,
        clubId: payload.club_id,
        clubName: payload.club_name,
        lineup: toLineup(payload.lineup).filter((item: LineupItem) => item.id !== null),
        popularityScore: payload.popularity_score
    }
}