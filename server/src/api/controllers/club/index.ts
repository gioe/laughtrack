import * as mapper from './mapper.js'
import * as service from '../../../database/services/ClubService.js'
import localCache from '../../../lib/local-cache.js'
import { Club } from '../../interfaces/club.interface.js'
import { CreateClubDTO, UpdateClubDTO } from '../../dto/club.dto.js'
import { GetAllClubsFilters } from '../../../database/dal/types.js'

const primaryCacheKey = 'clubs'

export const createAll = async(payload: CreateClubDTO[]): Promise<Club[]> => {
    const clubs = await service.createAll(payload);
    return clubs.map(club => {
        return mapper.toClub(club)
    })
}

export const create = async(payload: CreateClubDTO): Promise<Club> => {
    return mapper.toClub(await service.create(payload))
}

export const update = async (id: number, payload: UpdateClubDTO): Promise<Club> => {
    return mapper.toClub(await service.update(id, payload))
}

export const getById = async (id: string): Promise<Club> => {
    return mapper.toClub(await service.getById(id))
}

export const deleteById = async(id: number): Promise<Boolean> => {
    const isDeleted = await service.deleteById(id)
    return isDeleted
}

export const getAll = async (): Promise<Club[]> => {
    const clubs = await service.getAll().then((clubs) => clubs.map(mapper.toClub))
    
    if (clubs.length) {
        localCache.set(primaryCacheKey, clubs)
    }

    return clubs
}
