import { Show } from "../../../objects/class/show/Show"
import { ShowDetailDTO, ShowDetailPageData } from "./interface"

export const showDetailPageMapper = (data: ShowDetailDTO): ShowDetailPageData => {
    return {
        entity: new Show(data.response.data),
        total: data.response.total
    }
}
