import { JSON_KEYS } from "../../../../common/constants/keys.js"
import { ClubDetailsInterface, ClubInterface } from "../../../../common/interfaces/club.interface.js"
import { IClub, IClubDetails, IShowDetails } from "../../../../database/models.js"
import { toIShowArray, toShowDetailsInterface } from "../show/mapper.js"

export const toClubInterface = (payload: IClub): ClubInterface => {
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
        zipCode: payload.zip_code
    }
}

export const toClubDetailsInterface = (payload: IClubDetails): ClubDetailsInterface => {
    return {
        id: payload.id,
        name: payload.name,
        city: payload.city,
        longitude: payload.longitude,
        latitude: payload.latitude,
        baseUrl: payload.base_url,
        shows: payload.shows == undefined ? [] : payload.shows.map((show: IShowDetails) => toShowDetailsInterface(show)),
        zipCode: payload.zip_code
    }
}

export const clubArrayFromJson = (json: any) => {
    var clubArray: IClub[] = []

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

export const toIClub = (payload: ClubInterface): IClub => {
    return {
        id: payload.id,
        name: payload.name,
        popularity_score: payload.popularityScore,
        base_url: payload.baseUrl,
        schedule_page_url: payload.schedulePageUrl,
        timezone: payload.timezone,
        scraping_config: payload.scrapingConfig,
        city: payload.city,
        address: payload.address,
        latitude: payload.latitude,
        longitude: payload.longitude,
        shows: toIShowArray(payload.shows),
        zip_code: payload.zipCode,
    }
}
