import { Club } from '../../interfaces/club.interface.js'
import * as mapper from './mapper.js'
import * as service from '../../../database/services/ClubService.js'
import { CreateClubDTO, UpdateClubDTO } from '../../dto/club.dto.js'
import { GetAllClubsFilters } from '../../../database/dal/types.js'
import localCache from '../../../lib/local-cache.js'

const primaryCacheKey = 'clubs'

export const create = async(payload: CreateClubDTO): Promise<Club> => {
    return mapper.toClub(await service.create(payload))
}

export const update = async (id: number, payload: UpdateClubDTO): Promise<Club> => {
    return mapper.toClub(await service.update(id, payload))
}

export const getById = async (id: number): Promise<Club> => {
    return mapper.toClub(await service.getById(id))
}

export const deleteById = async(id: number): Promise<Boolean> => {
    const isDeleted = await service.deleteById(id)
    return isDeleted
}

export const getAll = async (filters: GetAllClubsFilters): Promise<Club[]> => {
    const clubs = await service.getAll(filters).then((clubs) => clubs.map(mapper.toClub))
    
    if (clubs.length) {
        localCache.set(primaryCacheKey, clubs)
    }

    return clubs
}
