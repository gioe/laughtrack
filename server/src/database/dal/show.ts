import pkg from 'lodash';
const { isEmpty } = pkg;

import Show, { ShowInput, ShowOutput } from "../models/Show.js"
import { GetAllShowsFilters } from "./types.js"

export const create = async (payload: ShowInput): Promise<ShowOutput> => {
    const show = await Show.create(payload)
    return show
}

export const update = async (id: number, payload: Partial<ShowInput>): Promise<ShowOutput> => {
    const show = await Show.findByPk(id)
    if (!show) {
        throw new Error('not found')
    }
    const updatedShow = await (show as Show).update(payload)
    return updatedShow
}

export const getById = async (id: number): Promise<ShowOutput> => {
    const show = await Show.findByPk(id)
    if (!show) {
        throw new Error('not found')
    }
    return show
}

export const deleteById = async (id: number): Promise<boolean> => {
    const deletedShowCount = await Show.destroy({
        where: {id}
    })
    return !!deletedShowCount
}

export const getAll = async (filters?: GetAllShowsFilters): Promise<ShowOutput[]> => {
    return Show.findAll()
}

export const checkSlugExists = async (slug: string): Promise<boolean> => {
    const comedianWithSlug = await Show.findOne({
        where: {
            slug
        }
    });

    return !isEmpty(comedianWithSlug)
}