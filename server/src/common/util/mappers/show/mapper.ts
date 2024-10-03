import { ShowInterface } from "../../../interfaces/client/show.interface.js"
import { CreateShowDTO } from "../../../interfaces/data/show.interface.js"
import { Show } from "../../../models/Show.js"
import { toComedianInterfaceArray } from "../comedian/mapper.js"

export const toDates = (payload: any): ShowInterface[] => {
    return payload.shows.map((show: any) => toShowInterface(show));
}

export const toShowInterface = (payload: any): ShowInterface => {
    return {
        id: payload.id,
        dateTime: payload.date_time,
        ticketLink: payload.ticket_link,
        clubId: payload.club_id,
        lineup: toComedianInterfaceArray(payload.lineup),
        popularityScore: payload.popularity_score
    }
}

export const toCreateShowDTO = (payload: Show): CreateShowDTO => {
    return {
        club_id: payload.clubId,
        date_time: payload.dateTime,
        ticket_link: payload.ticketLink,
    }
}

export const toCreateShowDTOArray = (payload?: Show[]): CreateShowDTO[] => {
    if (payload == undefined) return []
    return payload.map((show: Show) => toCreateShowDTO(show))
}
