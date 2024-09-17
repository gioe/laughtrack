import { ShowInterface } from '../../../common/interfaces/show.interface.js'
import { GetShowDetailsOutput } from '../../dto/show.dto.js'

export const toShow = (payload: GetShowDetailsOutput): ShowInterface => {
    return {
        id: payload.id,
        dateTime: payload.date_time,
        ticketLink: payload.ticket_link,
        comedians: [],
        clubId: payload.club_id
    }
}
