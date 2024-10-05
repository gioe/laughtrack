import { db } from '../../../database/index.js';
import { toHomeSearchResultInterface } from '../../../common/util/mappers/search/mapper.js';
import { HomeSearchResultInterface } from '../../../common/interfaces/client/searchResult.interface.js';
import { GetHomeSearchResultsDTO, GetHomeSearchResultsResponseDTO } from '../../../common/interfaces/data/search.interface.js';

export const getHomeSearchResults = async (request: GetHomeSearchResultsDTO, filter? : string): Promise<HomeSearchResultInterface | null> => {
    return db.search.getHomeSearchResults(request).then((result: GetHomeSearchResultsResponseDTO | null) => {
        if (result) return toHomeSearchResultInterface(result, filter)
        return null
    })
}