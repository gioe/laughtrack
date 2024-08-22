import pkg from 'lodash';
const { kebabCase } = pkg;

import * as clubDal from '../dal/club.js'
import { GetAllClubsFilters } from '../dal/types.js'
import { ClubInput, ClubOuput } from '../models/Club.js';

export const create = async (payload: ClubInput): Promise<ClubOuput> => {
    let slug = kebabCase(payload.name)
    const slugExists = await clubDal.checkSlugExists(slug)

    payload.slug = slugExists ? `${slug}-${Math.floor(Math.random() * 1000)}` : slug
    
    return clubDal.create(payload)
}

export const update = async (id: number, payload: Partial<ClubInput>): Promise<ClubOuput> => {
    if (payload.name) {
        let slug = kebabCase(payload.name)
        const slugExists = await clubDal.checkSlugExists(slug)

        payload.slug = slugExists ? `${slug}-${Math.floor(Math.random() * 1000)}` : slug
    }
    
    return clubDal.update(id, payload)
}

export const getById = (id: number): Promise<ClubOuput> => {
    return clubDal.getById(id)
}

export const deleteById = (id: number): Promise<boolean> => {
    return clubDal.deleteById(id)
}

export const getAll = (filters: GetAllClubsFilters): Promise<ClubOuput[]> => {
    return clubDal.getAll(filters)
}