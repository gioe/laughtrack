import * as clubDal from "../../../database/dal/club.js"
import * as mapper from "./mapper.js"
import { ClubInterface } from '../../../common/interfaces/club.interface.js'
import { CreateClubOutput } from '../../dto/club.dto.js'
import { runTasks } from "../../../common/util/promiseUtil.js"

export const createAll = async (): Promise<CreateClubOutput[]> => {
    return clubDal.getAllClubsFromFile()
    .then((payload: ClubInterface[]) => clubDal.createAllClubs(payload));
}

export const create = async(payload: ClubInterface): Promise<CreateClubOutput> => {
    return clubDal.createClub(payload)
}

export const getById = async (id: number): Promise<ClubInterface> => {
    return clubDal.getClubById(id)
    .then(output =>  mapper.toClub(output))
}

export const deleteById = async(id: number): Promise<Boolean> => {
    return clubDal.deleteClubById(id)
}

export const getAll = async (): Promise<ClubInterface[]> => {
    return clubDal.getAllClubs()
}

export const getAllClubsById = async (ids: number[]): Promise<ClubInterface[]> => {
    console.log(ids)
    const tasks = ids.map((id: number) => getById(id))
    return runTasks(tasks)
}
