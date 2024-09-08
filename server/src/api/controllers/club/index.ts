import * as clubDal from "../../../database/dal/club.js"
import * as mapper from "./mapper.js"

import { ClubInterface } from '../../interfaces/club.interface.js'
import { CreateClubDTO, CreateClubOutput } from '../../dto/club.dto.js'

export const createAll = async (): Promise<CreateClubOutput[]> => {
    return clubDal.getAllClubsFromFile()
    .then((payload) => clubDal.createAllClubs(payload));
}

export const create = async(payload: CreateClubDTO): Promise<CreateClubOutput> => {
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
