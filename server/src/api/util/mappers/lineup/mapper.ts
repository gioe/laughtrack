import { LineupItemInterface } from "../../../../common/interfaces/show.interface.js"
import { ILineupItem } from "../../../../database/models.js"


export const toLineupItemInterfaceArray = (payload: ILineupItem[]): LineupItemInterface[] => {
    return payload.map((item: ILineupItem) => toLineupItemInterface(item))
} 

export const toLineupItemInterface = (payload: ILineupItem): LineupItemInterface => {
    return {
        id: payload.id,
        name: payload.name,
        popularityScore: payload.popularity_score   
    }
}