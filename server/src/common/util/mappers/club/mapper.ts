import { JSON_KEYS } from "../../../constants/keys.js"
import { ClubInterface, ClubScrapingData } from "../../../interfaces/client/club.interface.js"
import { CreateClubDTO, GetClubWithShowsResponseDTO } from "../../../interfaces/data/club.interface.js"
import { GetShowResponseDTO } from "../../../interfaces/data/show.interface.js"
import { toShowInterface } from "../show/mapper.js"

export const toClubScrapingData = (payload: any): ClubScrapingData => {
    return {
        id: payload.id,
        name: payload.name,
        baseUrl: payload.base_url,
        schedulePageUrl: payload.schedule_page_url, 
        scrapingConfig: payload.scraping_config
    }
}
export const toClubInterface = (payload: GetClubWithShowsResponseDTO | null): ClubInterface | null => {
    if (payload == null) return null
    return {
        id: payload.id, 
        name: payload.name,
        baseUrl: payload.base_url,
        timezone: payload.timezone,
        city: payload.city,
        address: payload.address,
        popularityScore: payload.popularity_score,
        shows: payload.shows.map((show: GetShowResponseDTO) => toShowInterface(show)),
        zipCode: payload.zip_code
    }
}

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