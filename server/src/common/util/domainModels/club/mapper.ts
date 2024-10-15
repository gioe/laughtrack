import { JSON_KEYS } from "../../constants/keys.js"
import {
    GetClubDTO,
    CreateClubDTO,
    ClubInterface,
    ClubScrapingData
} from "../../../models/interfaces/club.interface.js"
import { toDates } from "../show/mapper.js"

export const clubArrayFromJson = (json: any) => {
    var clubArray: CreateClubDTO[] = []

    for (let index = 0; index < json[JSON_KEYS.clubs].length; index++) {
        const currentItem = json[JSON_KEYS.clubs][index];
        const currenItemClubs = currentItem[JSON_KEYS.clubDetails];

        currenItemClubs.forEach((club: any) => {
            clubArray.push({
                ...club,
                scraping_config: currentItem[JSON_KEYS.scrapingConfig],
                popularity_score: 0
            })
        })
    }
    return clubArray;
}

export const toClub = (payload: GetClubDTO): ClubInterface => {
    return {
        id: payload.id,
        name: payload.name,
        baseUrl: payload.base_url,
        city: payload.city,
        address: payload.address,
        popularityScore: payload.popularity_score,
        zipCode: payload.zip_code,
        dates: payload.dates !== undefined ? toDates(payload.dates) : []
    }
}

export const toClubScrapingData = (payload: GetClubDTO): ClubScrapingData => {
    return {
        id: payload.id,
        name: payload.name,
        baseUrl: payload.base_url,
        schedulePageUrl: payload.schedule_page_url,
        scrapingConfig: payload.scraping_config
    }
}
