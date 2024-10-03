import { JSON_KEYS } from "../../../constants/keys.js"
import { ClubInterface } from "../../../interfaces/client/club.interface.js"
import { CreateClubDTO } from "../../../interfaces/data/club.interface.js"
import { toShowInterface } from "../show/mapper.js"

export const toClubInterface = (payload: any): ClubInterface => {
    return {
        id: payload.id, 
        name: payload.name,
        baseUrl: payload.base_url,
        schedulePageUrl: payload.schedule_page_url,
        timezone: payload.timezone,
        scrapingConfig: payload.scraping_config,
        city: payload.city,
        address: payload.address,
        latitude: payload.latitude,
        longitude: payload.longitude,
        popularityScore: payload.popularity_score,
        shows: payload.shows == undefined ? [] : payload.shows.map((show: any) => toShowInterface(show)),
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