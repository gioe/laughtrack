import { generateClubPopularityData } from "../../../common/util/scoringUtil.js"
import { db } from '../../../database/index.js';
import { readFile } from '../../../common/util/storageUtil.js';
import { clubArrayFromJson, toClubInterface } from '../../../common/util/mappers/club/mapper.js';
import { CreateClubDTO } from "../../../common/interfaces/data/club.interface.js";
import { ClubInterface } from "../../../common/interfaces/client/club.interface.js";
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

export const getById = async (id: number): Promise<ClubInterface | null> => {
    return db.clubs.findById(id)
}

export const getAllDetailsByName = async (name: string):  Promise<ClubInterface | null> => {
    return db.clubs.findByNameWithAllDetails(name).then((response: ClubInterface | null) => {
        if (response) return toClubInterface(response)
        return null
    })
}

export const getBaseDetailsByName = async (name: string):  Promise<ClubInterface | null> => {
    return db.clubs.findByNameWithBaseDetails(name).then((response: ClubInterface | null) => {
        if (response) return toClubInterface(response)
        return null
    })
}

export const getAll = async (): Promise<ClubInterface[]> => {
    return db.clubs.all()
    .then((clubs: any[]) => clubs.map((club: any) => toClubInterface(club)))
}

export const getTrendingClubs = async (): Promise<ClubInterface[] | null> => {
    return db.clubs.getTrendingClubs()
}

export const getAllCities = async (): Promise<ClubInterface[] | null> => {
    return db.clubs.getAllCities()
}

export const generateScores = async (): Promise<null> => {
    return db.clubs.getAllPopularityData()
    .then((response: any[] | null) => toPopularityScores(response))
    .then((popularityScores: PopularityScoreDTO[] | null) => db.clubs.updateScores(popularityScores))
    
}
