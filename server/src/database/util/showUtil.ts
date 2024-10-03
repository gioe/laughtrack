import { toIShow } from "../../api/util/mappers/show/mapper.js";
import { ClubInterface } from "../../common/interfaces/club.interface.js";
import { Show } from "../../jobs/classes/models/Show.js";
import { writeFailureToFile } from "../../jobs/util/logUtil.js";
import { IShow } from "../models.js";

export const processShowsForStorage = (club: ClubInterface, shows: Show[]): IShow[] => {    
    if (shows.length == 0) writeFailureToFile(`No shows returned for ${club.name}`)

    var uniqueShows: IShow[] = []

    const validShows = shows
    .filter((show: Show) => show.lineup.length > 0)

    for (let index = 0; index < validShows.length - 1; index++) {
        const currentShow = validShows[index]
        
        var elementIndex = uniqueShows.findIndex(show => {
            return currentShow.dateTime == show.date_time &&
            currentShow.ticketLink == show.ticket_link
        });

        if (elementIndex == -1) {
            const covertedShow = toIShow(currentShow)
            uniqueShows.push(covertedShow)
        }
    }

    return uniqueShows
}