import pkg from 'lodash';
const { isEmpty } = pkg;

import Comedian, { ComedianInput, ComedianOuput } from '../models/Comedian.js'
import { GetAllComediansFilters } from './types.js'

export const create = async (payload: ComedianInput): Promise<ComedianOuput> => {
    const comedian = await Comedian.create(payload)
    return comedian
}

export const findOrCreate = async (payload: ComedianInput): Promise<ComedianOuput> => {
    const [comedian] = await Comedian.findOrCreate({
        where: {
            name: payload.name
        },
        defaults: payload
    })

    return comedian
}

export const update = async (id: number, payload: Partial<ComedianInput>): Promise<ComedianOuput> => {
    const comedian = await Comedian.findByPk(id)
    if (!comedian) {
        throw new Error('not found')
    }
    const updatedComedian = await (comedian as Comedian).update(payload)
    return updatedComedian
}

export const getById = async (id: number): Promise<ComedianOuput> => {
    const comedian = await Comedian.findByPk(id)
    if (!comedian) {
        throw new Error('not found')
    }
    return comedian
}

export const deleteById = async (id: number): Promise<boolean> => {
    const deletedComedianCount = await Comedian.destroy({
        where: {id}
    })
    return !!deletedComedianCount
}

export const getAll = async (filters?: GetAllComediansFilters): Promise<ComedianOuput[]> => {
    return Comedian.findAll()
}

export const checkSlugExists = async (slug: string): Promise<boolean> => {
    const comedianWithSlug = await Comedian.findOne({
        where: {
            slug
        }
    });

    return !isEmpty(comedianWithSlug)
}