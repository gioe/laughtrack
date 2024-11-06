import { getDB } from '../../database';
import { Club } from '../../objects/classes/club/Club';
import {
    PopularityScoreIODTO
} from "../../objects/interfaces";
import { GroupedSocialDataDTO } from '../../objects/interfaces/socialData.interface';
import * as socialDataMapper from '../../util/domainModels/socialData/mapper';

const { db } = getDB();

export const getAllClubs = async (ids: number[]): Promise<Club[]> => {
    return db.clubs.getAll().then((clubs: Club[]) => {
        if (ids.length > 0) {
            return clubs.filter((club: Club) => ids?.includes(club.id))
        }
        return clubs;
    })
}

export const generateScores = async (): Promise<null> => {
    return db.clubs.getAllPopularityData()
        .then((response: GroupedSocialDataDTO[] | null) => response ? socialDataMapper.toPopularityScores(response) : [])
        .then((popularityScores: PopularityScoreIODTO[]) => db.clubs.updateScores(popularityScores))
}
