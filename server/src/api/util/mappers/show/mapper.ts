import { ShowDetailsInterface, ShowInterface } from "../../../../common/interfaces/show.interface.js"
import { IShow, IShowDetails } from "../../../../database/models.js"
import { toIClub } from "../club/mapper.js"
import { toIComedianArray } from "../comedian/mapper.js"
import { toLineupItemInterfaceArray } from "../lineup/mapper.js"


export const toShowDetailsInterfaceArray = (payload: IShowDetails[]): ShowDetailsInterface[] => {
    return payload.map((show: IShowDetails) => toShowDetailsInterface(show))
}

export const toShowDetailsInterface = (payload: IShowDetails): ShowDetailsInterface => {
    return {
        id: payload.show_id,
        city: payload.city,
        club: {
            name: payload.club_name
        },
        lineup: toLineupItemInterfaceArray(payload.lineup),
        dateTime: payload.date_time,
        ticketLink: payload.ticket_link,
        popularityScore: payload.popularity_score
    }
}

export const toIShow = (payload: ShowInterface): IShow => {
    return {
        club: toIClub(payload.club),
        date_time: payload.dateTime,
        ticket_link: payload.ticketLink,
        popularity_score: payload.popularityScore,
        lineup: toIComedianArray(payload.lineup),
    }
}

export const toIShowArray = (payload?: ShowInterface[]): IShow[] => {
    if (payload == undefined) return []
    return payload.map((showInterface: ShowInterface) => toIShow(showInterface))
}