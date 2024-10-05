
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
        socialData: payload.social_data == undefined ? undefined : toSocialDataInterface(payload.social_data),
        dates: payload.dates == undefined ? undefined : toDates(payload.dates),
        popularityScore: payload.popularity_score
    }
}
