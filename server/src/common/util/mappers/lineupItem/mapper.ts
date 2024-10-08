import { LineupItem } from "../../../interfaces/client/comedian.interface copy.js"
import { LineupItemDTO } from "../../../interfaces/data/lineupItem.interface.js"


export const toLineupItemArray = (payload: LineupItemDTO[] | undefined, filter?: string): LineupItem[] => {
    if (payload == undefined) return []
    return payload.map((item: LineupItemDTO) => toLineupItem(item)).filter((item: LineupItem) => {
        if (filter) return item.name !== filter
        return true
    })
}

export const toLineupItem = (payload: LineupItemDTO): LineupItem => {
    return {
        id: payload.id,
        name: payload.name,
        popularityScore: payload.popularity_score,
    }
}
