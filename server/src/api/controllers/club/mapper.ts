import { ClubInterface } from '../../../common/interfaces/club.interface.js'
import { GetClubOutput } from '../../dto/club.dto.js'

export const toClub = (payload: GetClubOutput): ClubInterface => {
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
    }
}
