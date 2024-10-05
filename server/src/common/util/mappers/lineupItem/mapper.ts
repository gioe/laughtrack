import { LineupItem } from "../../../interfaces/client/comedian.interface copy.js"
import { LineupItemDTO } from "../../../interfaces/data/lineupItem.interface.js"


export const toLineupItemArray = (payload: LineupItemDTO[]): LineupItem[] => {
    return payload.map((item: LineupItemDTO) => toLineupItem(item))
}

export const toLineupItem = (payload: LineupItemDTO): LineupItem => {
    return {
        id: payload.id,
        name: payload.name,
        popularityScore: payload.popularity_score,
    }
}
