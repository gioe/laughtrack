import { db } from '../../../database/index.js';
import { toHomeSearchResultInterface } from '../../../common/util/mappers/search/mapper.js';
import { HomeSearchResultInterface } from '../../../common/interfaces/client/searchResult.interface.js';

export const getHomeSearchResults = async (request: any, filter? : string): Promise<HomeSearchResultInterface | null> => {
    return db.search.getHomeSearchResults(request).then((result: any | null) => {
        if (result) return toHomeSearchResultInterface(result, filter)
        return null
    })
}