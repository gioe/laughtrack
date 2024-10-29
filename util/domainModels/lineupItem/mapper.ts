import { CreateLineupItemDTO, LineupItem, LineupItemDTO } from "../../../interfaces"

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

export const toCreateLineupItemDTOArray = (comedianIds: number[], showId: number): CreateLineupItemDTO[] => {
    return comedianIds.map((id: number ) => {
        return {
            show_id: showId,
            comedian_id: id
        }
    })
}