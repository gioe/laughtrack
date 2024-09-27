import * as clubDal from "../../../database/dal/club.js"
import * as mapper from "./mapper.js"
import { ClubInterface } from '../../../common/interfaces/club.interface.js'
import { CreateClubOutput, TrendingClub } from '../../dto/club.dto.js'
import { runTasks } from "../../../common/util/promiseUtil.js"

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

export const getTrendingClubs = async (): Promise<TrendingClub[]> => {

    // const clubs = await clubController.getTrendingClubs()

    // const shows = await showController.getAll()
    // const groupedShows = groupByPropertyCount(shows, "clubId")

    // const topFive = Object.keys(groupedShows)
    //     .map((clubId: string) => {
    //         const showArray = groupedShows[clubId]
    //         const count = showArray.length
    //         return {
    //             clubId,
    //             count
    //         }
    //     })
    //     .sort((a, b) => b.count - a.count)
    //     .slice(0, 5)

    // const topFiveIds = topFive.map((object: any) => Number(object.clubId))

    // const clubsResponse = clubs.map((club: ClubInterface) => {
    //     return {
    //         id: club.id,
    //         name: club.name,
    //         url: club.baseUrl,
    //         count: 0
    //     }
    // })



    return clubDal.getTrendingClubs()
}
