import pkg from 'lodash';
const { isEmpty } = pkg;

import Show, { ShowCreationAttributes, ShowOutput } from "../models/Show.js"
import { GetAllShowsFilters } from "./types.js"


export const create = async (payload: ShowCreationAttributes): Promise<ShowOutput> => {
    const show = await Show.create(payload)
    return show
}

export const update = async (id: number, payload: Partial<ShowCreationAttributes>): Promise<ShowOutput> => {
    const show = await Show.findByPk(id)
    if (!show) {
        throw new Error('not found')
    }
    const updatedShow = await show.update(payload)
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

export const checkIfShowExists = async (payload: ShowCreationAttributes): Promise<boolean> => {
    const show = await Show.findOne({
        where: {
            clubId: payload.clubId,
            dateTime: payload.dateTime
        }
    });

    return !isEmpty(show)
}