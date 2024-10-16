import { GetShowResponseDTO, ShowInterface } from '../../../common/models/interfaces/show.interface.js';
import { CreateShowDTO } from '../../../common/models/interfaces/show.interface.js';
import {  GroupedPopularityScoreDTO, PopularityScoreIODTO } from '../../../common/models/interfaces/socialData.interface.js';
import { toShowInterface } from '../../../common/util/domainModels/show/mapper.js';
import { toPopularityScores } from '../../../common/util/domainModels/socialData/mapper.js';
import { db } from '../../../database/index.js';

export const add = async (show: CreateShowDTO): Promise<{id: number}> => {
    return db.shows.add(show);
}

export const getById = async (id: number): Promise<ShowInterface | null> => {
    return db.shows.findById(id).then((show: GetShowResponseDTO | null) => show ? toShowInterface(show) : null)
}

export const generateScores = async (): Promise<null> => {
    return db.shows.getAllLineupPopularityData()
    .then((response: GroupedPopularityScoreDTO[] | null) => response ? toPopularityScores(response) : [])
    .then((popularityScores: PopularityScoreIODTO[]) => popularityScores.length > 0 ? db.shows.updateScores(popularityScores) : null)
}
