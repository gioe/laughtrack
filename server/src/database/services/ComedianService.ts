import pkg from 'lodash';
const { kebabCase } = pkg;

import * as comedianDal from '../dal/comedian.js'
import { GetAllComediansFilters } from '../dal/types.js'
import { ComedianInput, ComedianOuput } from '../models/Comedian.js'


export const findOrCreate = async (payload: ComedianInput): Promise<ComedianOuput> => {
    let slug = kebabCase(payload.name)
    const slugExists = await comedianDal.checkSlugExists(slug)

    payload.slug = slugExists ? `${slug}-${Math.floor(Math.random() * 1000)}` : slug
    
    return comedianDal.findOrCreate(payload)
}

export const create = async (payload: ComedianInput): Promise<ComedianOuput> => {
    let slug = kebabCase(payload.name)
    const slugExists = await comedianDal.checkSlugExists(slug)

    payload.slug = slugExists ? `${slug}-${Math.floor(Math.random() * 1000)}` : slug
    
    return comedianDal.create(payload)
}

export const update = async (id: number, payload: Partial<ComedianInput>): Promise<ComedianOuput> => {
    if (payload.name) {
        let slug = kebabCase(payload.name)
        const slugExists = await comedianDal.checkSlugExists(slug)

        payload.slug = slugExists ? `${slug}-${Math.floor(Math.random() * 1000)}` : slug
    }
    
    return comedianDal.update(id, payload)
}

export const getById = (id: number): Promise<ComedianOuput> => {
    return comedianDal.getById(id)
}

export const deleteById = (id: number): Promise<boolean> => {
    return comedianDal.deleteById(id)
}

export const getAll = (filters: GetAllComediansFilters): Promise<ComedianOuput[]> => {
    return comedianDal.getAll(filters)
}