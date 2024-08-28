import pkg from 'lodash';
const { kebabCase } = pkg;

import * as showDal from '../dal/show.js'
import { ShowCreationAttributes, ShowOutput } from '../models/Show.js'
import { GetAllShowsFilters } from '../dal/types.js'
import { runTasks } from '../../util/promiseUtil.js';

export const updateOrCreateAll = async(payload: ShowCreationAttributes[]): Promise<ShowOutput[]> => {
    const tasks = payload.map(element => updateOrCreate(element))
    return runTasks(tasks)
}

export const updateOrCreate = async (payload: ShowCreationAttributes): Promise<ShowOutput> => {
    const showExists = await showDal.checkIfShowExists(payload) 

    if (showExists) {
        return create(payload)
    }

    return create(payload)
}

export const create = async (payload: ShowCreationAttributes): Promise<ShowOutput> => {
    return showDal.create(payload)
}

export const update = async (id: number, payload: Partial<ShowCreationAttributes>): Promise<ShowOutput> => {
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
