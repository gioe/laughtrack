import { ClubInterface } from "../interfaces/client/club.interface.js";
import { ShowInterface } from "../interfaces/client/show.interface.js";
import { CreateShowDTO } from "../interfaces/data/show.interface.js";
import { Show } from "../models/Show.js";
import { writeFailureToFile } from "./logUtil.js";
import { toCreateShowDTO } from "./mappers/show/mapper.js";

export const orderShows = (shows: ShowInterface[], filter?: string): ShowInterface[] => {
  return shows.sort((a: ShowInterface, b: ShowInterface) => {
      if (filter == 'date') {
          return new Date(a.dateTime).getTime() - new Date(b.dateTime).getTime();
      } else {
          return (b.popularityScore ?? 0) - (a.popularityScore ?? 0)

      }
  })
}

export const isLikelyShow = (inputString: string, showSignifiers?: string[]): boolean => {
  var isLikely = false;

  for (const singifier of showSignifiers ?? []) {
    if (inputString.toLowerCase().includes(singifier)) {
      isLikely = true;
    }
  }
  return isLikely
}

export const formatShowTicketLink = (ticketLink: string, club: ClubInterface): string => {
  return !ticketLink.includes("http") ? club.baseUrl + ticketLink : ticketLink
}

export const processShowsForStorage = (club: ClubInterface, shows: Show[]): CreateShowDTO[] => {    
    if (shows.length == 0) writeFailureToFile(`No shows returned for ${club.name}`)

    var uniqueShows: CreateShowDTO[] = []

    const validShows = shows
    .filter((show: Show) => show.lineup.length > 0)

    for (let index = 0; index < validShows.length - 1; index++) {
        const currentShow = validShows[index]
        
        var elementIndex = uniqueShows.findIndex(show => {
            return currentShow.dateTime == show.date_time &&
            currentShow.ticketLink == show.ticket_link
        });

        if (elementIndex == -1) {
            const covertedShow = toCreateShowDTO(currentShow)
            uniqueShows.push(covertedShow)
        }
    }

    return uniqueShows
}

