import { CreateLineupItemDTO, LineupItem, LineupItemDTO } from "../../../models/interfaces/lineupItem.interface.js"

export const toLineup = (payload: LineupItemDTO[]): LineupItem[] => {
    return payload.map((item: LineupItemDTO) => toLineupItem(item))
}

export const toLineupItem = (payload: LineupItemDTO): LineupItem => {
    return {
        id: payload.id,
        name: payload.name,
        popularityScore: payload.popularity_score,
    }
}

export const toCreateLineupItemDTOArray = (comedians: { id: number }[], showId: number): CreateLineupItemDTO[] => {
    return comedians.map((comedian: { id: number }) => {
        return {
            show_id: showId,
            comedian_id: comedian.id
        }
    })
}