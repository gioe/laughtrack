import { db } from '../../database';
import {
    ClubInterface,
    GroupedPopularityScoreDTO, PopularityScoreIODTO
} from "../../interfaces";
import * as socialDataMapper from '../../util/domainModels/socialData/mapper';

export const getAllClubs = async (): Promise<ClubInterface[]> => {
    return db.clubs.all()
}

export const getAllScrapingData = async (ids: number[]): Promise<ClubInterface[]> => {
    return db.clubs.all()
        .then((response: ClubInterface[] | null) => response ? 
        response.filter((value: ClubInterface) => {
            if (ids.length == 0) return true
            return ids.includes(value.id)
        })
    )
}

export const generateScores = async (): Promise<null> => {
    return db.clubs.getAllPopularityData()
        .then((response: GroupedPopularityScoreDTO[] | null) => response ? socialDataMapper.toPopularityScores(response) : [])
        .then((popularityScores: PopularityScoreIODTO[]) => db.clubs.updateScores(popularityScores))
}
