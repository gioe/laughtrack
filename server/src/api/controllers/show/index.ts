import { generateShowPopularityData } from '../../util/scoringUtil.js'
import { db } from '../../../database/index.js';
import { IShow, IShowPopularityData, IShowPoularityScore } from "../../../database/models.js"

export const createAll = async (allShows: IShow[]): Promise<null> => {
    return db.shows.addAll(allShows);
}

export const getById = async (id: number): Promise<IShow | null> => {
    return db.shows.findById(id);
}

export const generateScores = async (): Promise<null> => {
    const allData = await db.shows.getAllPopularityData();
    if (!allData) return null

    const updatedValues = allData.map((data: IShowPopularityData) => {
        return {
            id: data.id,
            popularity_score: generateShowPopularityData(data)
        }
    }) as IShowPoularityScore[];

    return db.shows.updateScores(updatedValues)
}


