import { GetAllShowsFilters } from '../../../database/dal/types.js'
import * as service from '../../../database/services/ShowService.js'
import { CreateShowDTO } from '../../dto/show.dto.js'
import { Show } from '../../interfaces/show.interface.js'
import * as mapper from './mapper.js'
import localCache from '../../../lib/local-cache.js'

const primaryCacheKey = 'shows'

export const updateOrCreateAll = async(payload: CreateShowDTO[]): Promise<void> => {
    await service.updateOrCreateAll(payload);
}

export const create = async(payload: CreateShowDTO): Promise<Show> => {
    return mapper.toShow(await service.create(payload))
}

export const getById = async (id: number): Promise<Show> => {
    return mapper.toShow(await service.getById(id))
}

export const deleteById = async(id: number): Promise<Boolean> => {
    const isDeleted = await service.deleteById(id)
    return isDeleted
}

export const getAll = async (filters: GetAllShowsFilters): Promise<Show[]> => {
    const shows = await service.getAll(filters).then((shows) => shows.map(mapper.toShow))
    
    if (shows.length) {
        localCache.set(primaryCacheKey, shows)
    }

    return shows
}