import pkg, { take } from 'lodash';
const { kebabCase } = pkg;

import * as clubDal from '../dal/club.js'
import { GetAllClubsFilters } from '../dal/types.js'
import { ClubCreationAttributes, ClubOuput } from '../models/Club.js';
import { runTasks } from '../../util/promiseUtil.js';

export const createAll = async (payload: ClubCreationAttributes[]): Promise<ClubOuput[]> => {  
    const tasks = payload.map(element => create(element))
    return runTasks(tasks)
}

export const create = async (payload: ClubCreationAttributes): Promise<ClubOuput> => {
    return clubDal.findOrCreate(payload)
}

export const update = async (id: number, payload: Partial<ClubCreationAttributes>): Promise<ClubOuput> => {
    return clubDal.update(id, payload)
}

export const getById = (id: string): Promise<ClubOuput> => {
    return clubDal.getById(id)
}

export const getByName = (name: string): Promise<ClubOuput> => {
    return clubDal.getByName(name)
}

export const deleteById = (id: number): Promise<boolean> => {
    return clubDal.deleteById(id)
}

export const getAll = (): Promise<ClubOuput[]> => {
    return clubDal.getAll()
}