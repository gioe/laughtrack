import { db } from '../../database';
import { toHomeSearchResultInterface } from '../../util/domainModels/search/mapper';
import { HomeSearchResultInterface, GetHomeSearchResultsDTO, GetHomeSearchResultsResponseDTO } from '../../interfaces';

export const getHomeSearchResults = async (request: GetHomeSearchResultsDTO): Promise<HomeSearchResultInterface | null> => {
    return db.search.getHomeSearchResults(request)
        .then((result: GetHomeSearchResultsResponseDTO | null) => result ? toHomeSearchResultInterface(result) : null)
}
