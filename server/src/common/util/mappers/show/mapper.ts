import { ShowInterface } from "../../../interfaces/client/show.interface.js"
import { CreateShowDTO, GetShowResponseDTO } from "../../../interfaces/data/show.interface.js"
import { Show } from "../../../models/Show.js"
import { toComedianInterfaceArray } from "../comedian/mapper.js"

export const toDates = (payload: any): ShowInterface[] => {
    return payload.shows.map((show: any) => toShowInterface(show));
}

export const toShowInterface = (payload: GetShowResponseDTO): ShowInterface => {
    return {
        id: payload.id,
        dateTime: payload.date_time,
        ticketLink: payload.ticket_link,
        clubId: payload.club_id,
        lineup: payload.lineup == undefined ? [] : toComedianInterfaceArray(payload.lineup),
        popularityScore: payload.popularity_score
    }
}


export const toCreateShowDTOArray = (payload?: Show[]): CreateShowDTO[] => {
    if (payload == undefined) return []
    return payload.map((show: Show) => show.asCreateShowDTO()).filter((dto: CreateShowDTO | null) => dto !== null)
}
