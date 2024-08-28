import pkg from 'lodash';
const { kebabCase } = pkg;

import * as comedianDal from '../dal/comedian.js'
import { GetAllComediansFilters } from '../dal/types.js'
import { ComedianCreationAttributes, ComedianOuput } from '../models/Comedian.js'
import { Comedian } from '../../api/interfaces/comedian.interface.js';
import { runTasks } from '../../util/promiseUtil.js';

export const getByIds = async (comedians: Comedian[]): Promise<string[]> => {
    const tasks = comedians.map(comedian => findOrCreate(comedian))
    return runTasks(tasks).then((comedians: ComedianOuput[]) => comedians.map(comedian => comedian.id))
}

export const findOrCreate = async (payload: ComedianCreationAttributes): Promise<ComedianOuput> => {
    return comedianDal.findOrCreate(payload)
}

export const create = async (payload: ComedianCreationAttributes): Promise<ComedianOuput> => {    
    return comedianDal.create(payload)
}

export const update = async (id: number, payload: Partial<ComedianCreationAttributes>): Promise<ComedianOuput> => {
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