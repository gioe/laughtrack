import { JSON_KEYS } from "../../constants/keys";
import { GetClubDTO, CreateClubDTO, ClubInterface } from "../../../interfaces";
import { toDates } from "../show/mapper";
import { toSocialDataInterface } from "../socialData/mapper";

export const clubArrayFromJson = (json: any) => {
    const clubArray: CreateClubDTO[] = [];

    for (const club of json[JSON_KEYS.clubs]) {
        const currenItemClubs = club[JSON_KEYS.clubDetails];

        currenItemClubs.forEach((club: any) => {
            clubArray.push({
                ...club,
                popularity_score: 0,
            });
        });
    }
    return clubArray;
};

export const toClub = (payload: GetClubDTO): ClubInterface => {
    return {
        id: payload.id,
        name: payload.name,
        baseUrl: payload.base_url,
        scrapingPageUrl: payload.schedule_page_url,
        city: payload.city,
        address: payload.address,
        zipCode: payload.zip_code,
        dates: payload.dates !== undefined ? toDates(payload.dates) : [],
        socialData: toSocialDataInterface(payload.social_data),
        tags: [],
        isFavorite: false,
    };
};
export const toClubs = (payload: GetClubDTO[]): ClubInterface[] => {
    return payload.map(toClub);
};
