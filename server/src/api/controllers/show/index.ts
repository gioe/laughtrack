import { ShowInterface } from '../../../common/models/interfaces/show.interface.js';
import { CreateShowDTO } from '../../../common/models/interfaces/show.interface.js';
import {  GroupedPopularityScoreDTO, PopularityScoreIODTO } from '../../../common/models/interfaces/socialData.interface.js';
import { flattenScoreCollections } from '../../../common/util/domainModels/socialData/mapper.js';
import { db } from '../../../database/index.js';

export const add = async (show: CreateShowDTO): Promise<{id: number}> => {
    return db.shows.add(show);
}

export const getById = async (id: number): Promise<ShowInterface | null> => {
    return db.shows.findById(id);
}

export const generateScores = async (): Promise<null> => {
    return db.shows.getAllLineupPopularityData()
    .then((response: GroupedPopularityScoreDTO[] | null) => flattenScoreCollections(response))
    .then((popularityScores: PopularityScoreIODTO[]) =>   db.shows.updateScores(popularityScores))
}
