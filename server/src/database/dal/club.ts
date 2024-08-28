import pkg from 'lodash';
const { isEmpty } = pkg;

import Club, { ClubCreationAttributes, ClubOuput } from '../models/Club.js'
import { GetAllClubsFilters } from './types.js'


export const create = async (payload: ClubCreationAttributes): Promise<ClubOuput> => {
    const club = await Club.create(payload)
    return club
}

export const findOrCreate = async (payload: ClubCreationAttributes): Promise<ClubOuput> => {
    const [club] = await Club.findOrCreate({
        where: {
            name: payload.name
        },
        defaults: payload
    })

    return club
}

export const update = async (id: number, payload: Partial<ClubCreationAttributes>): Promise<ClubOuput> => {
    const club = await Club.findByPk(id)
    if (!club) {
        throw new Error('not found')
    }
    const updatedClub = await club.update(payload)
    return updatedClub
}

export const getById = async (id: string): Promise<ClubOuput> => {
    const club = await Club.findByPk(id)
    if (!club) {
        throw new Error('not found')
    }
    return club
}

export const getByName = async (name: string): Promise<ClubOuput> => {
   
    const club = await Club.findOne({
        where: {
            name,
        }
    });

    if (!club) {
        throw new Error('not found')
    }
    
    return club
}


export const deleteById = async (id: number): Promise<boolean> => {
    const deletedClubCount = await Club.destroy({
        where: {id}
    })
    return !!deletedClubCount
}

export const getAll = async (filters?: GetAllClubsFilters): Promise<ClubOuput[]> => {
    return Club.findAll()
}

export const checkIfClubExists = async (payload: ClubCreationAttributes): Promise<boolean> => {
    const club = await Club.findOne({
        where: {
            name: payload.name,
        }
    });

    return !isEmpty(club)
}