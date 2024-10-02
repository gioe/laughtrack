import { HomeSearchResultInterface } from '../../../common/interfaces/searchResult.interface.js';
import { db } from '../../../database/index.js';
import { IHomeSearchResult } from '../../../database/models.js';
import { toHomeSearchResult } from './mapper.js';

export const getHomeSearchResults = async (request: any, filter? : string): Promise<HomeSearchResultInterface | null> => {
    return db.search.getHomeSearchResults(request).then((result: IHomeSearchResult | null) => {
        if (result) return toHomeSearchResult(result, filter)
        return null
    })
}