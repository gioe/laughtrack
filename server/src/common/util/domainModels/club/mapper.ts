import { JSON_KEYS } from "../../../constants/keys.js"
import {
    GetClubDTO,
    CreateClubDTO,
    GetClubsDTO,
    ClubInterface,
    ClubScrapingData
} from "../../../models/interfaces/club.interface.js"
import { toDates } from "../show/mapper.js"

export const toClubScrapingDataArray = (payload: GetClubDTO[] | null): ClubScrapingData[] => {
    if (payload == null) return []
    return payload.map((value: GetClubDTO) => toClubScrapingData(value))
        .filter((value: ClubScrapingData | null) => value !== null)
}

export const toClubScrapingData = (payload: GetClubDTO | null): ClubScrapingData | null => {
    if (payload == null) return null
    return {
        id: payload.id,
        name: payload.name,
        baseUrl: payload.base_url,
        schedulePageUrl: payload.schedule_page_url,
        scrapingConfig: payload.scraping_config
    }
}

export const toClubInterfaceArray = (payload: GetClubDTO[] | null, query?: string): ClubInterface[] => {
    if (payload == null) return []
    return payload.map((value: GetClubDTO) => toClubInterface(value))
        .filter((value: ClubInterface | null) => value !== null)
        .filter((comedian: ClubInterface) => {
            if (query) return comedian.name.toLocaleLowerCase().includes(query.toLocaleLowerCase())
            return true
        })
}

export const toClubInterface = (payload: GetClubDTO | null, filter?: string, sort?: string): ClubInterface | null => {
    if (payload == null) return null
    return {
        id: payload.id,
        name: payload.name,
        baseUrl: payload.base_url,
        timezone: payload.timezone,
        city: payload.city,
        address: payload.address,
        popularityScore: payload.popularity_score,
        dates: toDates(payload.dates, filter, sort),
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

export const toGetClubsDto = (payload: any): GetClubsDTO => {
    return {
        query: payload.query == '' ? undefined : payload.query,
        sort: payload.sort == '' ? undefined : payload.sort
    }
}

