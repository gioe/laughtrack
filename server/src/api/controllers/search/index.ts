import { db } from '../../../database/index.js';
import { toHomeSearchResultInterface } from '../../../common/util/mappers/search/mapper.js';
import { HomeSearchResultInterface } from '../../../common/interfaces/client/searchResult.interface.js';
import { GetHomeSearchResultsDTO, GetHomeSearchResultsResponseDTO } from '../../../common/interfaces/data/search.interface.js';
import { filterAndSort } from '../../../common/util/showUtil.js';

export const getHomeSearchResults = async (request: GetHomeSearchResultsDTO): Promise<HomeSearchResultInterface | null> => {
    return db.search.getHomeSearchResults(request)
    .then((result: GetHomeSearchResultsResponseDTO | null) => {
        if (result == null) return null
        const filteredResult = filterAndSort(result, request)
        return toHomeSearchResultInterface(filteredResult)
    })
}
