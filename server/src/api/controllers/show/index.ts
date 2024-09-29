import { ShowInterface, ShowPopularityScore } from "../../../common/interfaces/show.interface.js"
import { generateShowPopularityData } from '../../util/scoringUtil.js'
import { db } from '../../../database/index.js';
import { IShow, IShowPopularityData } from "../../../database/models.js"

export const createAll = async (allShows: ShowInterface[]): Promise<null> => {
    return db.shows.addAll(allShows);
}

export const create = async (show: ShowInterface): Promise<IShow> => {
    return db.shows.add(show);
}

export const getById = async (id: number): Promise<IShow | null> => {
    return db.shows.findById(id);
}

export const deleteById = async (id: number): Promise<number> => {
    return db.shows.remove(id)
}

export const getAll = async (): Promise<IShow[] | null> => {
    return db.shows.all()
}

export const getSearchResults = async (request: any) => {
    return db.shows.getSearchResults(request)
}

export const generateScores = async (): Promise<null> => {
    const allData = await db.shows.allPopularityData();
    if (!allData) return null

    const updatedValues = allData.map((data: IShowPopularityData) => {
        return {
            id: data.id,
            popularity_score: generateShowPopularityData(data)
        }
    }) as ShowPopularityScore[];

    return db.shows.updateScores(updatedValues)
}


