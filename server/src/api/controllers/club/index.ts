import { db } from '../../../database/index.js';
import { readFile } from '../../../common/util/storageUtil.js';
import { toPopularityScores } from '../../../common/util/domainModels/socialData/mapper.js';
import { 
    clubArrayFromJson, 
    toClub, 
    toClubScrapingData
} from '../../../common/util/domainModels/club/mapper.js';
import {
    CreateClubDTO,
    GetCitiesResponseDTO,
    GetClubDTO,
    ClubInterface,
    ClubScrapingData
} from "../../../common/models/interfaces/club.interface.js";
import { GroupedPopularityScoreDTO, PopularityScoreIODTO } from '../../../common/models/interfaces/socialData.interface.js';

const getAllClubsFromFile = async () => {
    return readFile(process.env.CLUBS_FILE_NAME as string)
        .then((clubsJson: any) => clubArrayFromJson(clubsJson))
}

export const addAll = async (): Promise<null> => {
    const clubs: CreateClubDTO[] = await getAllClubsFromFile()
    return db.clubs.addAll(clubs);
}

export const getAllClubs = async (): Promise<ClubInterface[]> => {
    return db.clubs.all()
        .then((response: GetClubDTO[] | null) => response ? response.map((value: GetClubDTO) => toClub(value)) : [])
}

export const getByName = async (name: string): Promise<ClubInterface | null> => {
    return db.clubs.getByName(name)
        .then((response: GetClubDTO | null) => {
            return response ? toClub(response) : null
        })
}

export const getAllScrapingData = async (ids: number[]): Promise<ClubScrapingData[]> => {
    return db.clubs.all()
        .then((response: GetClubDTO[] | null) => response ? 
        response.filter((value: GetClubDTO) => {
            if (ids.length == 0) return true
            return ids.includes(value.id)
        })
        .map((value: GetClubDTO) => toClubScrapingData(value)) : []
    )
}

export const getAllCities = async (): Promise<string[]> => {
    return db.clubs.getAllCities()
        .then((response: GetCitiesResponseDTO[]) => response.map((item: GetCitiesResponseDTO) => item.city))
}

export const generateScores = async (): Promise<null> => {
    return db.clubs.getAllPopularityData()
        .then((response: GroupedPopularityScoreDTO[] | null) => response ? toPopularityScores(response) : [])
        .then((popularityScores: PopularityScoreIODTO[]) => db.clubs.updateScores(popularityScores))
}
