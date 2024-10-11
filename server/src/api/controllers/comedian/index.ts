import { db } from '../../../database/index.js';
import { toComedianInterface, toComedianInterfaceArray } from "../../../common/util/domainModels/comedian/mapper.js";
import { CreateComedianDTO, GetComediansDTO, GetComedianResponseDTO, ComedianInterface } from "../../../common/models/interfaces/comedian.interface.js";
import { CreateFavoriteComedianDTO } from "../../../common/models/interfaces/favorite.interface.js";
import { GetSocialDataDTO, PopularityScoreIODTO, UpdateSocialDataDTO } from "../../../common/models/interfaces/socialData.interface.js";
import { generatePopularityScore } from '../../../common/util/scoringUtil.js';
import { sortComedians } from '../../../common/util/domainModels/comedian/comedianUtil.js';
import { toPopularityScores } from '../../../common/util/domainModels/socialData/mapper.js';

export const addAll = async (comedians: CreateComedianDTO[]): Promise<{ id: number }[]> => {
    return db.comedians.addAll(comedians);
}

export const getAllComedians = async (payload: GetComediansDTO): Promise<ComedianInterface[]> => {
    return db.comedians.all()
        .then((comedians: GetComedianResponseDTO[]) => {
            const comedianResponse = toComedianInterfaceArray(comedians, payload.query);
            return payload.sort ? sortComedians(comedianResponse, payload.sort) : comedianResponse
        })
}

export const getAllComediansWithFavorites = async (payload: GetComediansDTO): Promise<ComedianInterface[]> => {
    return db.comedians.allWithFavorites(payload.userId)
    .then((comedians: GetComedianResponseDTO[]) => {
        const comedianResponse = toComedianInterfaceArray(comedians, payload.query);
        return payload.sort ? sortComedians(comedianResponse, payload.sort) : comedianResponse
    })}

export const getByName = async (name: string, sort?: string): Promise<ComedianInterface | null> => {
    return db.comedians.findByName(name)
        .then((response: GetComedianResponseDTO | null) => toComedianInterface(response, undefined, sort))
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

export const updateSocialData = async (payload: any): Promise<boolean | null> => {
    const { instagramAccount, instagramFollowers, youtubeAccount, youtubeFollowers, tiktokAccount, tiktokFollowers, website, id } = payload;
    
    const instagramFollowerInt = parseInt(instagramFollowers as string)
    const tiktokFollowerInt = parseInt(tiktokFollowers as string)
    const youtubeFollowerInt = parseInt(youtubeFollowers as string)
    const instagramFollowerCount = !isNaN(instagramFollowerInt) ? instagramFollowerInt : 0;
    const tiktokFollowerCount = !isNaN(tiktokFollowerInt) ? tiktokFollowerInt : 0;
    const youtubeFollowerCount = !isNaN(youtubeFollowerInt) ? youtubeFollowerInt : 0;

    const idNumber = parseInt(id as string)

    var input = {
        instagram_followers: instagramFollowerCount,
        tiktok_followers: tiktokFollowerCount,
        youtube_followers: youtubeFollowerCount,
        popularity_score: generatePopularityScore({
            id: idNumber,
            instagram_followers: instagramFollowerCount,
            tiktok_followers: tiktokFollowerCount,
            youtube_followers: youtubeFollowerCount
        }),
        id: idNumber,
        instagram_account: instagramAccount,
        youtube_account: youtubeAccount,
        tiktok_account: tiktokAccount,
        website: website
    } as UpdateSocialDataDTO

    return db.comedians.updateSocialData(input)
}
