import { ClubInterface } from "../../common/interfaces/club.interface.js";
import { ShowInterface } from "../../common/interfaces/show.interface.js";
import { Show } from "../../jobs/classes/models/Show.js";
import { writeFailureToFile } from "../../jobs/util/logUtil.js";

export const processShows = (club: ClubInterface, shows: Show[]) => {    
    if (shows.length == 0) writeFailureToFile(`No shows returned for ${club.name}`)

    const validShows = shows
    .filter((show: Show) => show.comedians.length > 0)

    var uniqueShows: Show[] = []

    for (let index = 0; index < validShows.length - 1; index++) {
        const currentShow = validShows[index]
        
        var elementIndex = uniqueShows.findIndex(show => {
            return currentShow.dateTimeString == show.dateTimeString &&
            currentShow.ticketLink == show.ticketLink
        });

        if (elementIndex == -1) {
            uniqueShows.push(currentShow)
        }
    }

    return uniqueShows
}