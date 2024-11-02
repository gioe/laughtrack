import { ShowInterface, GetShowResponseDTO } from "../../../interfaces";
import { toSocialDataInterface } from "../socialData/mapper";
import { toLineup } from "../comedian/mapper";

export const toDates = (
    payload: GetShowResponseDTO[] | undefined,
): ShowInterface[] => {
    return payload == undefined
        ? []
        : payload.map((show: GetShowResponseDTO) => toShowInterface(show));
};

export const toShowInterface = (payload: GetShowResponseDTO): ShowInterface => {
    return {
        id: payload.id,
        price: parseFloat(payload.price),
        name: payload.name,
        clubName: payload.club_name,
        ticketLink: payload.ticket_link,
        dateTime: payload.date_time,
        socialData: toSocialDataInterface(payload.social_data),
        lineup: toLineup(payload.lineup),
        tags: [],
    };
};
