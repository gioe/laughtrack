import { Comedian } from '../../interfaces/comedian.interface.js'
import * as mapper from './mapper.js'
import * as service from '../../../database/services/ComedianService.js'
import { CreateComedianDTO, UpdateComedianDTO } from '../../dto/comedian.dto.js'
import { GetAllComediansFilters } from '../../../database/dal/types.js'
import localCache from '../../../lib/local-cache.js'

const primaryCacheKey = 'comedians'

export const findOrCreate = async(payload: CreateComedianDTO): Promise<Comedian> => {
    return mapper.toComedian(await service.findOrCreate(payload))
}

export const create = async(payload: CreateComedianDTO): Promise<Comedian> => {
    return mapper.toComedian(await service.create(payload))
}

export const update = async (id: number, payload: UpdateComedianDTO): Promise<Comedian> => {
    return mapper.toComedian(await service.update(id, payload))
}

export const getById = async (id: number): Promise<Comedian> => {
    return mapper.toComedian(await service.getById(id))
}

export const deleteById = async(id: number): Promise<Boolean> => {
    const isDeleted = await service.deleteById(id)
    return isDeleted
}

export const getAll = async (filters: GetAllComediansFilters): Promise<Comedian[]> => {
    const comedians = await service.getAll(filters).then((comedians) => comedians.map(mapper.toComedian))
    
    if (comedians.length) {
        localCache.set(primaryCacheKey, comedians)
    }

    return comedians
}
