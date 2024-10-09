import { db } from '../../../database/index.js';
import { toComedianInterface, toComedianInterfaceArray } from "../../../common/util/mappers/comedian/mapper.js";
import { ComedianInterface } from "../../../common/interfaces/client/comedian.interface.js";
import { CreateComedianDTO, GetComedianResponseDTO } from "../../../common/interfaces/data/comedian.interface.js";
import { CreateFavoriteComedianDTO } from "../../../common/interfaces/data/favorite.interface.js";
import { GetSocialDataDTO, PopularityScoreIODTO, UpdateSocialDataDTO } from "../../../common/interfaces/data/socialData.interface.js";
import { toPopularityScores } from '../../../common/util/mappers/socialData/mapper.js';

export const addAll = async (comedians: CreateComedianDTO[]): Promise<{id: number}[]> => {
    return db.comedians.addAll(comedians);
}

export const getAllComedians = async (query?: string): Promise<ComedianInterface[]> => {
    return db.comedians.all()
    .then((comedians: GetComedianResponseDTO[]) => {
        console.log(comedians[0])
        return toComedianInterfaceArray(comedians, query)
    })
}

export const getAllComediansWithFavorites = async (userId: number, query?: string): Promise<ComedianInterface[]> => {
    return db.comedians.allWithFavorites(userId)
    .then((comedians: GetComedianResponseDTO[]) => toComedianInterfaceArray(comedians, query))
}

export const getByName = async (name: string, sort?: string): Promise<ComedianInterface | null> => {
    return db.comedians.findByName(name)
    .then((response: GetComedianResponseDTO | null) => toComedianInterface(response, name, sort))
}

export const getAllFavorites = async (userId: number): Promise<ComedianInterface[]> => {
    return db.comedians.getAllFavorites(userId)
    .then((comedians: GetComedianResponseDTO[] | null) => toComedianInterfaceArray(comedians))
}

export const getTrendingComedians = async (): Promise<ComedianInterface[] | null> => {
    return db.comedians.getTrendingComedians()
}

export const generateScores = async (): Promise<null> => {
    return db.comedians.getAllSocialData()
    .then((response: GetSocialDataDTO[] | null) => toPopularityScores(response))
    .then((popularityScores: PopularityScoreIODTO[] | null) => db.comedians.updateScores(popularityScores))
}

export const favoriteComedian = async (payload: CreateFavoriteComedianDTO): Promise<boolean> => {
    if (payload.is_favorite) return db.favorites.remove(payload)
    return db.favorites.add(payload)
}

export const updateSocialData = async (payload: UpdateSocialDataDTO): Promise<boolean | null> => {
    return db.comedians.updateSocialData(payload)
}
