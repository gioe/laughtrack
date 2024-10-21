import { db } from '../../../database/index.js';
import { toComedian, toComedianArray, toComedianFilter } from "../../../common/util/domainModels/comedian/mapper.js";
import { CreateComedianDTO, GetComediansDTO, GetComedianResponseDTO, ComedianInterface, ComedianFilterInterface } from "../../../common/models/interfaces/comedian.interface.js";
import { CreateFavoriteComedianDTO } from "../../../common/models/interfaces/favorite.interface.js";
import { GetSocialDataDTO, PopularityScoreIODTO, UpdateSocialDataDTO } from "../../../common/models/interfaces/socialData.interface.js";
import { toPopularityScores } from '../../../common/util/domainModels/socialData/mapper.js';

export const addAll = async (comedians: CreateComedianDTO[]): Promise<{ id: number }[]> => {
    return db.comedians.addAll(comedians);
}

export const getAllComedians = async (payload: GetComediansDTO): Promise<ComedianInterface[]> => {

    const task = payload.userId ? db.comedians.allWithFavorites(payload.userId) : db.comedians.all()

    return task
        .then((response: GetComedianResponseDTO[] | null) => response ? response.map((item: any) => toComedian(item)) : [])
}

export const getAllFavorites = async (userId: number): Promise<ComedianInterface[]> => {
    return db.comedians.getAllFavorites(userId)
        .then((response: GetComedianResponseDTO[] | null) => response ? response.map((item: any) => toComedian(item)) : [])
}

export const getByName = async (name: string): Promise<ComedianInterface | null> => {
    return db.comedians.findByName(name)
        .then((response: GetComedianResponseDTO | null) => response ? toComedian(response) : null)
}

export const getTrendingComedians = async (): Promise<ComedianInterface[] | null> => {
    return db.comedians.getTrendingComedians()
    .then((response: GetComedianResponseDTO[] | null) => response ? toComedianArray(response) : null)

}

export const generateScores = async (): Promise<null> => {
    return db.comedians.getAllSocialData()
        .then((response: GetSocialDataDTO[] | null) => response ? toPopularityScores(response) : [])
        .then((popularityScores: PopularityScoreIODTO[]) => db.comedians.updateScores(popularityScores))
}

export const favoriteComedian = async (payload: CreateFavoriteComedianDTO, isFavorite: boolean): Promise<boolean> => {
    return isFavorite ? db.favorites.remove(payload) : db.favorites.add(payload)
}

export const updateSocialData = async (payload: UpdateSocialDataDTO): Promise<boolean | null> => {
    return db.comedians.updateSocialData(payload)
}

export const getAllComedianFilters = async (): Promise<ComedianFilterInterface[]> => {

    return db.comedians.all()
        .then((response: GetComedianResponseDTO[] | null) => response ? response.map((item: any) => toComedianFilter(item)) : [])
}

export const updateParentage = async (childId: number): Promise<null> => {
    return db.comedians.updateParentage({
        id: childId,
        is_parent: false
    })
}