import { ShowOutput } from "../../../database/models/Show.js"
import { Show } from "../../interfaces/show.interface.js"

export const toShow = (show: ShowOutput): Show => {
    return {
        dateTime: show.dateTime,
        ticketLink: show.ticketLink,
        comedianIds: show.comedianIds,
        clubId: show.clubId,
        id: show.id
    }
}