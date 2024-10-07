import { db } from '../../../database/index.js';
import { readFile } from '../../../common/util/storageUtil.js';
import { clubArrayFromJson, toClubInterface, toClubScrapingData } from '../../../common/util/mappers/club/mapper.js';
import { CreateClubDTO, GetCitiesResponseDTO, GetClubPopularityDataDTO, GetClubWithShowsResponseDTO } from "../../../common/interfaces/data/club.interface.js";
import { ClubInterface, ClubScrapingData } from "../../../common/interfaces/client/club.interface.js";
import { PopularityScoreDTO } from "../../../common/interfaces/data/popularityScore.interface.js";
import { toPopularityScores } from "../../../common/util/mappers/socialData/mapper.js";

const getAllClubsFromFile = async () => {
    return readFile(process.env.CLUBS_FILE_NAME as string)
    .then((clubsJson: any) => clubArrayFromJson(clubsJson))
}

export const addAll = async (): Promise<null> => {
    const clubs: CreateClubDTO[] = await getAllClubsFromFile()
    return db.clubs.addAll(clubs);
}

export const getByName = async (name: string): Promise<ClubInterface | null> => {
    return db.clubs.getByName(name)
    .then((response: GetClubWithShowsResponseDTO | null) => toClubInterface(response))
}

export const getAll = async (): Promise<ClubScrapingData[]> => {
    return db.clubs.all()
    .then((clubs: ClubScrapingData[]) => clubs.map((club: ClubScrapingData) => toClubScrapingData(club)))
}

export const getAllCities = async (): Promise<string[]> => {
    return db.clubs.getAllCities().then((response: GetCitiesResponseDTO[] | null) => {
        return response == null ? [] : response.map((item: GetCitiesResponseDTO) => item.city)
    })
}

export const generateScores = async (): Promise<null> => {
    return db.clubs.getAllPopularityData()
    .then((response: GetClubPopularityDataDTO[] | null) => toPopularityScores(response))
    .then((popularityScores: PopularityScoreDTO[] | null) => db.clubs.updateScores(popularityScores))
    
}
