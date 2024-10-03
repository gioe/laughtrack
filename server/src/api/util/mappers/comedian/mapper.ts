import { ComedianDetailsInterface, ComedianInterface } from "../../../../common/interfaces/comedian.interface.js"
import { IComedian, IComedianDetails, IShowDetails } from "../../../../database/models.js"
import { toShowDetailsInterface, toShowDetailsInterfaceArray } from "../show/mapper.js"
import { toSocialDataInterface } from "../socialData/mapper.js"

export const toComedianInterface = (payload: IComedian): ComedianInterface => {
    return {
        id: payload.id,
        name: payload.name,
        instagramAccount: payload.instagram_account,
        instagramFollowers: payload.instagram_followers,
        tikTokAccount: payload.tiktok_account,
        tiktokFollowers: payload.tiktok_followers,
        isPseudonym: payload.is_pseudonym,
        website: payload.website,
        poplarityScore: payload.popularity_score,
        nonComedian: payload.non_comedian
    }
}

export const toComedianDetailsInterface = (payload: IComedianDetails): ComedianDetailsInterface => {
    return {
        id: payload.id,
        name: payload.name,
        socialData: toSocialDataInterface(payload.social_data),
        dates: toShowDetailsInterfaceArray(payload.dates)
    }
}

export const toIComedianArray = (payload: ComedianInterface[]): IComedian[] => {
    return payload.map((comedianInterface: ComedianInterface) => toIComedian(comedianInterface))
}

export const toIComedian = (payload: ComedianInterface): IComedian => {
    return {
        id: payload.id,
        name: payload.name,
        instagram_account: payload.instagramAccount ?? "",
        instagram_followers: payload.instagramFollowers,
        tiktok_account: payload.tikTokAccount ?? "",
        tiktok_followers: payload.tiktokFollowers,
        website: payload.website ?? "",
        is_pseudonym: payload.isPseudonym,
        popularity_score: payload.poplarityScore,
        non_comedian: payload.nonComedian
    }
}