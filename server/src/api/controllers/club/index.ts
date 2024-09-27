import * as clubDal from "../../../database/dal/club.js"
import { ClubInterface } from '../../../common/interfaces/club.interface.js'
import { CreateClubOutput } from '../../dto/club.dto.js'
import { generateClubPopularityData } from "../../util/scoringUtil.js"

export const createAll = async (): Promise<CreateClubOutput[]> => {
    const clubs: ClubInterface[] = await clubDal.getAllClubsFromFile()
    var responses: CreateClubOutput[] = []

    for (let i = 0; i < clubs.length; i++) {
        const club = clubs[i]
        const output = await create(club)
        responses.push(output)
    }
    
    return responses
}

export const create = async (payload: ClubInterface): Promise<CreateClubOutput> => {
    return clubDal.createClub(payload)
}

export const getById = async (id: number): Promise<ClubInterface> => {
    return clubDal.getClubById(id)
}

export const deleteById = async (id: number): Promise<Boolean> => {
    return clubDal.deleteClubById(id)
}

export const getAll = async (): Promise<ClubInterface[]> => {
    return clubDal.getAllClubs()
}

export const getClubsByLocation = async (location: string): Promise<ClubInterface[]> => {
    return clubDal.getClubsInLocation(location)
}

export const getTrendingClubs = async (): Promise<ClubInterface[]> => {
    return clubDal.getTrendingClubs()
}

export const generateScores = async (): Promise<boolean> => {
    const clubs: ClubInterface[] = []
    
    const updatedValues = clubs.map((club: ClubInterface) => {
        return {
            id: club.id,
            score: generateClubPopularityData(club.shows ?? [])
        }
    })

    return clubDal.updateScores(updatedValues)
}
