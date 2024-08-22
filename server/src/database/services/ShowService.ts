import pkg from 'lodash';
const { kebabCase } = pkg;

import * as showDal from '../dal/show.js'
import { ShowInput, ShowOutput } from '../models/Show.js'
import { GetAllShowsFilters } from '../dal/types.js'

export const create = async (payload: ShowInput): Promise<ShowOutput> => {
    let slug = kebabCase(payload.ticketLink)
    const slugExists = await showDal.checkSlugExists(slug)

    payload.slug = slugExists ? `${slug}-${Math.floor(Math.random() * 1000)}` : slug
    
    return showDal.create(payload)
}

export const update = async (id: number, payload: Partial<ShowInput>): Promise<ShowOutput> => {
    if (payload.ticketLink) {
        let slug = kebabCase(payload.ticketLink)
        const slugExists = await showDal.checkSlugExists(slug)

        payload.slug = slugExists ? `${slug}-${Math.floor(Math.random() * 1000)}` : slug
    }
    
    return showDal.update(id, payload)
}

export const getById = (id: number): Promise<ShowOutput> => {
    return showDal.getById(id)
}

export const getAll = (filters: GetAllShowsFilters): Promise<ShowOutput[]> => {
    return showDal.getAll(filters)
}
export const deleteById = (id: number): Promise<boolean> => {
    return showDal.deleteById(id)
}
