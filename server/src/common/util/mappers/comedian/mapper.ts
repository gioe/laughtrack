
import { ComedianInterface } from "../../../interfaces/client/comedian.interface.js"
import { toDates } from "../show/mapper.js"
import { toSocialDataInterface } from "../socialData/mapper.js"

export const toComedianInterfaceArray = (payload: any): ComedianInterface[] => {
    return payload.map((item: any) => toComedianInterface(item))
}

export const toComedianInterface = (payload: any): ComedianInterface => {
    return {
        id: payload.id,
        name: payload.name,
        socialData: toSocialDataInterface(payload.social_data),
        dates: toDates(payload.dates),
        popularityScore: payload.popularity_score
    }
}
