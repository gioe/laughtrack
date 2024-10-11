import { db } from '../../../database/index.js';
import { toHomeSearchResultInterface } from '../../../common/util/domainModels/search/mapper.js';
import { HomeSearchResultInterface } from '../../../common/models/interfaces/search.interface.js';
import { GetHomeSearchResultsDTO, GetHomeSearchResultsResponseDTO } from '../../../common/models/interfaces/search.interface.js';

export const getHomeSearchResults = async (request: GetHomeSearchResultsDTO): Promise<HomeSearchResultInterface | null> => {
    return db.search.getHomeSearchResults(request)
    .then((result: GetHomeSearchResultsResponseDTO | null) => result ? toHomeSearchResultInterface(result) : null)
}
