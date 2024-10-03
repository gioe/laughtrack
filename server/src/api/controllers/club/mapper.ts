import { JSON_KEYS } from '../../../common/constants/keys.js'
import { ClubDetailsInterface, ClubInterface } from '../../../common/interfaces/club.interface.js'
import { IClub, IClubDetails, IShowDetails } from '../../../database/models.js'
import { toShowDetails } from '../show/mapper.js'

export const toClub = (payload: IClub): ClubInterface => {
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
        imageName: payload.image_name,
        popularityScore: payload.popularity_score
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

export const toClubDetails = (payload: IClubDetails): ClubDetailsInterface => {
    return {
        id: payload.id,
        name: payload.name,
        city: payload.city,
        longitude: payload.longitude,
        latitude: payload.latitude,
        baseUrl: payload.base_url,
        dates: payload.dates == undefined ? [] : payload.dates.map((show: IShowDetails) => toShowDetails(show)),
        zipCode: payload.zip_code
    }
}
