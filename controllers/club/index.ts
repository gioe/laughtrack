import { db } from '../../database';
import { readFile } from '../../util/storageUtil';
import {
    CreateClubDTO,
    GetCitiesResponseDTO,
    GetClubDTO,
    ClubInterface,
    ClubScrapingData,
    GroupedPopularityScoreDTO, PopularityScoreIODTO
} from "../../interfaces";
import * as socialDataMapper from '../../util/domainModels/socialData/mapper';
import * as clubMapper from '../../util/domainModels/club/mapper';

const getAllClubsFromFile = async () => {
    return readFile(process.env.CLUBS_FILE_NAME as string)
        .then((clubsJson: any) => clubMapper.clubArrayFromJson(clubsJson))
}

export const addAll = async (): Promise<null> => {
    const clubs: CreateClubDTO[] = await getAllClubsFromFile()
    return db.clubs.addAll(clubs);
}

export const getAllClubs = async (): Promise<ClubInterface[]> => {
    return db.clubs.all()
        .then((response: GetClubDTO[] | null) => response ? response.map((value: GetClubDTO) => clubMapper.toClub(value)) : [])
}

export const getByName = async (name: string): Promise<ClubInterface | null> => {
    return db.clubs.getByName(name)
        .then((response: GetClubDTO | null) => {
            return response ? clubMapper.toClub(response) : null
        })
}

export const getAllScrapingData = async (ids: number[]): Promise<ClubScrapingData[]> => {
    return db.clubs.all()
        .then((response: GetClubDTO[] | null) => response ? 
        response.filter((value: GetClubDTO) => {
            if (ids.length == 0) return true
            return ids.includes(value.id)
        })
        .map((value: GetClubDTO) => clubMapper.toClubScrapingData(value)) : []
    )
}

export const getAllCities = async (): Promise<string[]> => {
    return db.clubs.getAllCities()
        .then((response: GetCitiesResponseDTO[]) => response.map((item: GetCitiesResponseDTO) => item.city))
}

export const generateScores = async (): Promise<null> => {
    return db.clubs.getAllPopularityData()
        .then((response: GroupedPopularityScoreDTO[] | null) => response ? socialDataMapper.toPopularityScores(response) : [])
        .then((popularityScores: PopularityScoreIODTO[]) => db.clubs.updateScores(popularityScores))
}
