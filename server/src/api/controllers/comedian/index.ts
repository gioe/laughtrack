import { generateComedianPopularityScore } from "../../../common/util/scoringUtil.js"
import { db } from '../../../database/index.js';
import { toComedianInterface, toComedianInterfaceArray } from "../../../common/util/mappers/comedian/mapper.js";
import { ComedianInterface } from "../../../common/interfaces/client/comedian.interface.js";
import { CreateComedianDTO, GetComedianResponseDTO } from "../../../common/interfaces/data/comedian.interface.js";
import { CreateFavoriteComedianDTO } from "../../../common/interfaces/data/favorite.interface.js";

export const addAll = async (comedians: CreateComedianDTO[]): Promise<{id: number}[]> => {
    return db.comedians.addAll(comedians);
}

export const getAllComedians = async (query?: string): Promise<ComedianInterface[]> => {
    return db.comedians.all()
    .then((comedians: GetComedianResponseDTO[]) => toComedianInterfaceArray(comedians, query))
}

export const getAllComediansWithFavorites = async (userId: number, query?: string): Promise<ComedianInterface[]> => {
    return db.comedians.allWithFavorites(userId)
    .then((comedians: GetComedianResponseDTO[]) => toComedianInterfaceArray(comedians, query))
}

export const getByName = async (name: string): Promise<ComedianInterface | null> => {
    return db.comedians.findByName(name)
    .then((response: GetComedianResponseDTO | null) => toComedianInterface(response))
}

export const getAllFavorites = async (userId: number): Promise<ComedianInterface[]> => {
    return db.comedians.getAllFavorites(userId)
    .then((comedians: GetComedianResponseDTO[] | null) => toComedianInterfaceArray(comedians))
}

export const getTrendingComedians = async (): Promise<ComedianInterface[] | null> => {
    return db.comedians.getTrendingComedians()
}

export const generateScores = async (): Promise<null> => {
    const allData = await db.comedians.allPopularityData();
    if (!allData) return null

    const updatedValues = allData.map((data: any) => {
        return {
            id: data.id,
            popularity_score: generateComedianPopularityScore(data)
        }
    }) 

    return db.comedians.updateScores(updatedValues)
}


export const favoriteComedian = async (payload: CreateFavoriteComedianDTO): Promise<boolean> => {
    if (payload.is_favorite) return db.favorites.remove(payload)
    return db.favorites.add(payload)
}
