import { ShowInterface } from "../../../interfaces/client/show.interface.js"
import { GetDateDTO } from "../../../interfaces/data/comedian.interface.js"
import { CreateShowDTO, GetShowResponseDTO } from "../../../interfaces/data/show.interface.js"
import { Show } from "../../../models/Show.js"
import { toLineupItemArray } from "../lineupItem/mapper.js"

export const toDates = (payload: GetDateDTO[] | GetShowResponseDTO[] | undefined): ShowInterface[] | undefined => {
    if (payload == undefined) return undefined
    return payload.map((show: GetDateDTO | GetShowResponseDTO) => toShowInterface(show));
}

export const toShowInterface = (payload: GetShowResponseDTO | GetDateDTO): ShowInterface => {
    return {
        id: payload.id,
        dateTime: payload.date_time,
        ticketLink: payload.ticket_link,
        clubId: payload.club_id,
        clubName: payload.club_name,
        lineup: payload.lineup == undefined ? [] : toLineupItemArray(payload.lineup),
        popularityScore: payload.popularity_score
    }
}


export const toCreateShowDTOArray = (payload?: Show[]): CreateShowDTO[] => {
    if (payload == undefined) return []
    return payload.map((show: Show) => show.asCreateShowDTO()).filter((dto: CreateShowDTO | null) => dto !== null)
}
