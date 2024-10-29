import {
    GetDateDTO,
    ShowInterface, GetShowResponseDTO,
} from "../../../interfaces";
import { toTagInterfaceArray } from "../tag/mapper";
import { toSocialDataInterface } from "../socialData/mapper";

export const toDates = (payload: GetDateDTO[] | GetShowResponseDTO[]): ShowInterface[] => {
    return payload.map((show: GetDateDTO | GetShowResponseDTO) => toShowInterface(show));
}

export const toShowInterface = (payload: GetShowResponseDTO | GetDateDTO): ShowInterface => {
    return {
        id: payload.id,
        name: payload.name,
        dateTime: payload.date_time,
        ticketLink: payload.ticket_link,
        socialData: toSocialDataInterface(payload.social_data),
        clubId: payload.club_id,
        clubName: payload.club_name,
        lineup: [],

        // lineup: toLineup(payload.lineup).filter((comedian: ComedianInterface) => item.id !== null),
        popularityScore: payload.popularity_score,
        tags: payload.tags ? toTagInterfaceArray(payload.tags) : [],
        price: parseFloat(payload.price)
    }
}