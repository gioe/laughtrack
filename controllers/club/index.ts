import { getDB } from '../../database';
import {
    ClubInterface,
    GroupedPopularityScoreDTO, PopularityScoreIODTO
} from "../../interfaces";
import * as socialDataMapper from '../../util/domainModels/socialData/mapper';

const { db } = getDB();

export const getAllClubs = async (ids?: number[]): Promise<ClubInterface[]> => {
    return db.clubs.getAll().then((clubs: ClubInterface[]) => {
        if (ids) {
            return clubs.filter((club: ClubInterface) => ids?.includes(club.id))
        }
        return clubs;
    })
}


export const generateScores = async (): Promise<null> => {
    return db.clubs.getAllPopularityData()
        .then((response: GroupedPopularityScoreDTO[] | null) => response ? socialDataMapper.toPopularityScores(response) : [])
        .then((popularityScores: PopularityScoreIODTO[]) => db.clubs.updateScores(popularityScores))
}
