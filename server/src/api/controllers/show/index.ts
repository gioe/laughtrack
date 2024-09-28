import { GetFilteredShowsRequest, ShowScore } from '../../dto/show.dto.js'
import { ShowInterface } from "../../../common/interfaces/show.interface.js"
import { generateShowPopularityData } from '../../util/scoringUtil.js'
import { db } from '../../../database/index.js';
import { IShow } from "../../../database/models.js"

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

export const getSearchResults = async (request: GetFilteredShowsRequest) => {
    return db.shows.getSearchResults(request)
}

export const updateScores = async (scores: ShowScore[]) => {
    return db.shows.updateScores(scores)
}

export const generateScores = async (): Promise<boolean[]> => {
    const shows: ShowInterface[] = []
    
    const updatedValues = shows.map((show: ShowInterface) => {
        return {
            id: show.id,
            score: generateShowPopularityData(show.comedians ?? [])
        }
    })
    return []
}


