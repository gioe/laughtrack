import { ClubInterface } from '../../interfaces/club.interface.js'
import { GetClubOutput } from '../../dto/club.dto.js'

export const toClub = async(payload: GetClubOutput): Promise<ClubInterface> => {
    return {
        id: payload.id, 
        name: payload.name,
        baseUrl: payload.base_url,
        schedulePageUrl: payload.schedule_page_url,
        timezone: payload.timezone,
        scrapingConfig: payload.scraping_config
    }
}
