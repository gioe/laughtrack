import * as showService from '../../../database/services/ShowService.js'
import * as clubService from '../../../database/services/ClubService.js'
import * as comedianService from '../../../database/services/ComedianService.js'
import * as mapper from './mapper.js'
import localCache from '../../../lib/local-cache.js'
import { GetAllShowsFilters } from '../../../database/dal/types.js'
import { CreateShowDTO } from '../../dto/show.dto.js'
import { Show } from '../../interfaces/show.interface.js'
import { runTasks } from '../../../util/promiseUtil.js'

const primaryCacheKey = 'shows'

export const updateOrCreateAll = async(payloads: CreateShowDTO[]): Promise<Show[]> => {
    const shows = payloads.map(payload => updateOrCreate(payload))
    return runTasks(shows)
}

export const updateOrCreate = async(payload: CreateShowDTO): Promise<Show> => {
    const club = await clubService.getByName(payload.club.name)
    const comedianIds = await comedianService.getByIds(payload.comedians)

    return mapper.toShow(await showService.updateOrCreate({
        comedianIds: comedianIds,
        dateTime: payload.dateTime,
        ticketLink: payload.ticketLink,
        clubId: club.id
    }))

}

export const getById = async (id: number): Promise<Show> => {
    return mapper.toShow(await showService.getById(id))
}

export const deleteById = async(id: number): Promise<Boolean> => {
    const isDeleted = await showService.deleteById(id)
    return isDeleted
}

export const getAll = async (filters: GetAllShowsFilters): Promise<Show[]> => {
    const shows = await showService.getAll(filters).then((shows) => shows.map(mapper.toShow))
    
    if (shows.length) {
        localCache.set(primaryCacheKey, shows)
    }

    return shows
}