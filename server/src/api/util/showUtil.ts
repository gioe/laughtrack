import { ShowDetailsInterface } from "../../common/interfaces/show.interface.js";

export const orderShows = (shows: ShowDetailsInterface[], filter?: string): ShowDetailsInterface[] => {
    return shows
    .sort((a: ShowDetailsInterface, b: ShowDetailsInterface) => {
        if (filter == 'date') {
            return new Date(a.dateTime).getTime() - new Date(b.dateTime).getTime();
        } else {
            return b.popularityScore - a.popularityScore;
        }
    })
}

