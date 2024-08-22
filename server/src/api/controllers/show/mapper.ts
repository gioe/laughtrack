import { ShowOutput } from "../../../database/models/Show.js"
import { Show } from "../../interfaces/show.interface.js"

export const toShow = (show: ShowOutput): Show => {
    return {
        id: show.id,
        dateTime: show.dateTime,
        ticketLink: show.ticketLink,
        createdAt: show.createdAt,
        updatedAt: show.updatedAt,
        deletedAt: show.deletedAt 
    }
}