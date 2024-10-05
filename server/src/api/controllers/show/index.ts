import { ShowInterface } from '../../../common/interfaces/client/show.interface.js';
import { GroupedPopularityScores } from '../../../common/interfaces/data/popularityScore.interface.js';
import { CreateShowDTO } from '../../../common/interfaces/data/show.interface.js';
import { generateShowPopularityData } from '../../../common/util/scoringUtil.js'
import { db } from '../../../database/index.js';

export const add = async (show: CreateShowDTO): Promise<{id: number}> => {
    return db.shows.add(show);
}

export const getById = async (id: number): Promise<ShowInterface | null> => {
    return db.shows.findById(id);
}

export const generateScores = async (): Promise<null> => {
    const allData = await db.shows.getAllPopularityData();
    if (!allData) return null

    const updatedValues = allData.map((data: GroupedPopularityScores) => {
        return {
            id: data.id,
            popularity_score: generateShowPopularityData(data)
        }
    })

    return db.shows.updateScores(updatedValues)
}


