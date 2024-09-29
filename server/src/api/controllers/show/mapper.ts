import { ShowInterface } from '../../../common/interfaces/show.interface.js'
import { IShow } from '../../../database/models.js'

export const toShow = (payload: IShow): ShowInterface => {
    return {
        id: payload.id,
        dateTime: payload.date_time,
        ticketLink: payload.ticket_link,
        clubId: payload.club.id,
        popularityScore: payload.popularity_score
    }
}
