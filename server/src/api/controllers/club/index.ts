import { ClubDetailsInterface, ClubInterface } from '../../../common/interfaces/club.interface.js'
import { generateClubPopularityData } from "../../util/scoringUtil.js"
import { db } from '../../../database/index.js';
import { IClub, IClubDetails, IClubPopularityData } from "../../../database/models.js";
import { readFile } from '../../util/storageUtil.js';
import { clubArrayFromJson, toClub, toClubDetails } from './mapper.js';

const getAllClubsFromFile = async () => {
    return readFile(process.env.CLUBS_FILE_NAME as string)
    .then((clubsJson: any) => clubArrayFromJson(clubsJson))
}

export const addAll = async (): Promise<null> => {
    const clubs: ClubInterface[] = await getAllClubsFromFile()
    return db.clubs.addAll(clubs);
}

export const add = async (payload: ClubInterface): Promise<IClub> => {
    return db.clubs.add(payload)
}

export const getById = async (id: number):  Promise<IClub | null> => {
    return db.clubs.findById(id)
}

export const getByName = async (name: string):  Promise<ClubDetailsInterface | null> => {
    return db.clubs.findByName(name).then((response: IClubDetails | null) => {
        if (response) return toClubDetails(response)
        return null
    })
}


export const deleteById = async (id: number): Promise<number> => {
    return db.clubs.delete(id)
}

export const getAll = async (): Promise<ClubInterface[]> => {
    return db.clubs.all().then((clubs: IClub[]) => clubs.map((club: IClub) => toClub(club)))
}

export const getClubsByLocation = async (location: string): Promise<IClub[] | null> => {
    return db.clubs.findByCity(location)
}

export const getTrendingClubs = async (): Promise<IClub[] | null> => {
    return db.clubs.getTrendingClubs()
}

export const getAllCities = async (): Promise<IClub[] | null> => {
    return db.clubs.getAllCities()
}

export const generateScores = async (): Promise<null> => {
    const allData = await db.clubs.allPopularityData();
    if (!allData) return null
    
    const updatedValues = allData.map((data: IClubPopularityData) => {
        return {
            id: data.id,
            popularity_score: generateClubPopularityData(data)
        }
    }) 

    return db.clubs.updateScores(updatedValues)
}
