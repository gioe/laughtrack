import { HomeSearchResultInterface } from '../../../common/interfaces/searchResult.interface.js'
import { ShowDetailsInterface } from '../../../common/interfaces/show.interface.js'
import { IHomeSearchResult, IShowDetails } from '../../../database/models.js'
import { toShowDetails } from '../show/mapper.js'

export const toHomeSearchResult = (payload: IHomeSearchResult, filter?: string): HomeSearchResultInterface => {
    return {
        city: payload.city,
        shows: createAndOrderShows(payload.shows, filter)
    }
}

export const createAndOrderShows = (shows: IShowDetails[], filter?: string): ShowDetailsInterface[] => {
    return shows.map((show: IShowDetails) => toShowDetails(show))
    .sort((a: ShowDetailsInterface, b: ShowDetailsInterface) => {
        if (filter == 'date') {
            return new Date(a.dateTime).getTime() - new Date(b.dateTime).getTime();
        } else {
            return b.popularityScore - a.popularityScore;

        }
    })
}


