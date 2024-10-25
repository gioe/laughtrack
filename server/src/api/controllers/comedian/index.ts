import { db } from '../../../database/index.js';
import { toComedian, toComedianArray, toComedianFilter } from "../../../common/util/domainModels/comedian/mapper.js";
import { CreateComedianDTO, 
    GetComediansDTO,
     GetComedianResponseDTO, 
     ComedianInterface,
      ComedianFilterInterface, 
      UpdateComedianHashDTO} from "../../../common/models/interfaces/comedian.interface.js";
import { CreateFavoriteComedianDTO } from "../../../common/models/interfaces/favorite.interface.js";
import { GetSocialDataDTO, PopularityScoreIODTO, UpdateSocialDataDTO } from "../../../common/models/interfaces/socialData.interface.js";
import { toPopularityScores } from '../../../common/util/domainModels/socialData/mapper.js';
import { generateComedianHash } from '../../../common/util/domainModels/comedian/hash.js';

export const addAll = async (comedians: CreateComedianDTO[]): Promise<string[]> => {
    const hashedComedians = comedians.map((comedian: CreateComedianDTO) => {
        return {
            name: comedian.name,
            uuid_id: generateComedianHash(comedian.name)
        }
    });
    
    return db.comedians.addAll(hashedComedians)
    .then(() => hashedComedians.map((comedian) => comedian.uuid_id));
}

export const getAllComedians = async (payload?: GetComediansDTO): Promise<ComedianInterface[]> => {

    const task = payload?.userId ? db.comedians.allWithFavorites(payload.userId) : db.comedians.all()

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

export const writeHashes = async (hashedComedians: UpdateComedianHashDTO[]) => {
    return db.comedians.writeHashes(hashedComedians);
}

export const getByUUIDs = async (uuids: string[]): Promise<number[]> => {
    return db.comedians.getIds(uuids).then((response: {id: number}[]) => response.map((value: {id:number}) => value.id))
}

