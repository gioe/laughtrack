import { HomeSearchResultInterface } from '../../../common/interfaces/searchResult.interface.js'
import { IHomeSearchResult, IShowDetails } from '../../../database/models.js'
import { toShowDetails } from '../show/mapper.js'

export const toHomeSearchResult = (payload: IHomeSearchResult): HomeSearchResultInterface => {
    return {
        city: payload.city,
        shows: payload.shows.map((show: IShowDetails) => toShowDetails(show))
    }
}
