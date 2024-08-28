import { ClubOuput } from "../../../database/models/Club.js"
import { Club } from "../../interfaces/club.interface.js"

export const toClub = (club: ClubOuput): Club => {
    return {
        id: club.id,
        name: club.name,
        slug: club.slug,
        baseUrl: club.baseUrl,
        schedulePageUrl: club.schedulePageUrl,
        timezone: club.timezone,
        scrapingConfig: club.scrapingConfig,
        createdAt: club.createdAt,
        updatedAt: club.updatedAt,
        deletedAt: club.deletedAt
    }
}