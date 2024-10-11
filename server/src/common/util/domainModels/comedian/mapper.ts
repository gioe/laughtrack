
import { ComedianInterface, GetComedianResponseDTO, GetComediansDTO } from "../../../models/interfaces/comedian.interface.js"
import { toDates } from "../show/mapper.js"
import { toSocialDataInterface } from "../socialData/mapper.js"

export const toComedianInterfaceArray = (payload: GetComedianResponseDTO[]): ComedianInterface[] => {
    return payload.map((item: any) => toComedian(item))
}

export const toComedian = (payload: GetComedianResponseDTO): ComedianInterface => {
    return {
        id: payload.id,
        name: payload.name,
        socialData: toSocialDataInterface(payload.social_data),
        dates: toDates(payload.dates),
        favoriteId: payload.favorite_id == null ? undefined : payload.favorite_id,
        popularityScore: payload.popularity_score
    }
}

export const toGetComediansDTO = (payload: any): GetComediansDTO => {
    return {
        userId: payload.currentUser.id == '' ? undefined : payload.currentUser.id,
    }
}
