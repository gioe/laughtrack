
import { ComedianInterface } from "../../../interfaces/client/comedian.interface.js"
import { GetComedianResponseDTO } from "../../../interfaces/data/comedian.interface.js"
import { toDates } from "../show/mapper.js"
import { toSocialDataInterface } from "../socialData/mapper.js"


export const toComedianInterfaceArray = (payload: GetComedianResponseDTO[] | null, query?: string): ComedianInterface[] => {
    if (payload == null ) return []

    return payload.map((item: any) => toComedianInterface(item))
    .filter((comedian: ComedianInterface | null) => comedian !== null)
    .filter((comedian: ComedianInterface) => {
        if (comedian == null) return false
        if (query) return comedian.name.toLocaleLowerCase().includes(query.toLocaleLowerCase())
        return true
    })
}

export const toComedianInterface = (payload: GetComedianResponseDTO | null | undefined): ComedianInterface | null=> {
    if (payload == null || payload == undefined) return null
    return {
        id: payload.id,
        name: payload.name,
        socialData: toSocialDataInterface(payload.social_data),
        dates: toDates(payload.dates),
        favoriteId: payload.favorite_id == null ? undefined : payload.favorite_id
    }
}
