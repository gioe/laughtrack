import { db } from '../../../database/index.js';
import { readFile } from '../../../common/util/storageUtil.js';
import { clubArrayFromJson, toClubInterface, toClubInterfaceArray, toClubScrapingDataArray } from '../../../common/util/domainModels/club/mapper.js';
import { 
    CreateClubDTO,
    GetCitiesResponseDTO, 
    GetClubDTO, 
    GetClubsDTO, 
    ClubInterface,
    ClubScrapingData 
} from "../../../common/models/interfaces/club.interface.js";
import { GroupedPopularityScoreDTO, PopularityScoreIODTO } from '../../../common/models/interfaces/socialData.interface.js';
import { averagePopularityScore } from '../../../common/util/scoringUtil.js';
import { sortClubs } from '../../../common/util/domainModels/club/clubUtil.js';

const getAllClubsFromFile = async () => {
    return readFile(process.env.CLUBS_FILE_NAME as string)
    .then((clubsJson: any) => clubArrayFromJson(clubsJson))
}

export const addAll = async (): Promise<null> => {
    const clubs: CreateClubDTO[] = await getAllClubsFromFile()
    return db.clubs.addAll(clubs);
}

export const getByName = async (name: string, filter?: string, sort?: string): Promise<ClubInterface | null> => {
    return db.clubs.getByName(name)
    .then((response: GetClubDTO | null) => toClubInterface(response, filter, sort))
}

export const getAllClubs =  async (payload: GetClubsDTO): Promise<ClubInterface[]> => {
    return db.clubs.all()
    .then((clubs: GetClubDTO[]) => {
        const clubResponse = toClubInterfaceArray(clubs, payload.query);
        return payload.sort ? sortClubs(clubResponse, payload.sort) : clubResponse
    })
    
}

export const getAllScrapingData = async (): Promise<ClubScrapingData[]> => {
    return db.clubs.all()
    .then((clubs: GetClubDTO[]) => toClubScrapingDataArray(clubs))
}

export const getAllCities = async (): Promise<string[]> => {
    return db.clubs.getAllCities().then((response: GetCitiesResponseDTO[] | null) => {
        return response == null ? [] : response.map((item: GetCitiesResponseDTO) => item.city)
    })
}

export const generateScores = async (): Promise<null> => {
    return db.clubs.getAllPopularityData()
    .then((response: GroupedPopularityScoreDTO[] | null) => toUpdatePopularityScoreDTOArray(response))
    .then((popularityScores: PopularityScoreIODTO[] | null) => db.clubs.updateScores(popularityScores))
}

const toUpdatePopularityScoreDTOArray = (response: GroupedPopularityScoreDTO[] | null): PopularityScoreIODTO[] => {
    if (response == null) return []
    return response.map((item: GroupedPopularityScoreDTO) => {
        return {
            id: item.id,
            popularity_score: averagePopularityScore(item.scores)
        } as PopularityScoreIODTO
    })
}

