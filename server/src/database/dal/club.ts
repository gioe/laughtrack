import pkg from 'lodash';
const { isEmpty } = pkg;

import Club, { ClubInput, ClubOuput } from '../models/Club.js'
import { GetAllClubsFilters } from './types.js'


export const create = async (payload: ClubInput): Promise<ClubOuput> => {
    const club = await Club.create(payload)
    return club
}

export const findOrCreate = async (payload: ClubInput): Promise<ClubOuput> => {
    const [club] = await Club.findOrCreate({
        where: {
            name: payload.name
        },
        defaults: payload
    })

    return club
}

export const update = async (id: number, payload: Partial<ClubInput>): Promise<ClubOuput> => {
    const club = await Club.findByPk(id)
    if (!club) {
        throw new Error('not found')
    }
    const updatedClub = await (club as Club).update(payload)
    return updatedClub
}

export const getById = async (id: number): Promise<ClubOuput> => {
    const club = await Club.findByPk(id)
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

export const checkSlugExists = async (slug: string): Promise<boolean> => {
    const clubWithSlug = await Club.findOne({
        where: {
            slug
        }
    });

    return !isEmpty(clubWithSlug)
}