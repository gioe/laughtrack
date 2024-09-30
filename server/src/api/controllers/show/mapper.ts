import { LineupItemInterface, ShowDetailsInterface, ShowInterface } from '../../../common/interfaces/show.interface.js'
import { ILineupItem, IShow, IShowDetails } from '../../../database/models.js'
import { toClub } from '../club/mapper.js'

export const toShow = (payload: IShow): ShowInterface => {
    return {
        id: payload.id,
        dateTime: payload.date_time,
        ticketLink: payload.ticket_link,
        club: toClub(payload.club),
        popularityScore: payload.popularity_score
    }
}

export const toShowDetails = (payload: IShowDetails): ShowDetailsInterface => {
    return {
        id: payload.show_id,
        city: payload.city,
        club: {
            name: payload.club_name
        },
        lineup: payload.lineup.map((lineupItem: ILineupItem) => toLineupItem(lineupItem)),
        dateTime: payload.date_time,
        ticketLink: payload.ticket_link
    }
}
export const toLineupItem = (payload: ILineupItem): LineupItemInterface => {
    return {
        id: payload.id,
        name: payload.name,
        popularityScore: payload.popularity_score   
    }
}