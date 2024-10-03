import { HomeSearchResultInterface } from '../../../common/interfaces/searchResult.interface.js';
import { db } from '../../../database/index.js';
import { IHomeSearchResult } from '../../../database/models.js';
import { toHomeSearchResultInterface } from '../../util/mappers/search/mapper.js';

export const getHomeSearchResults = async (request: any, filter? : string): Promise<HomeSearchResultInterface | null> => {
    return db.search.getHomeSearchResults(request).then((result: IHomeSearchResult | null) => {
        if (result) return toHomeSearchResultInterface(result, filter)
        return null
    })
}