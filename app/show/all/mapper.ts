import { Show } from "../../../objects/class/show/Show"
import { ShowDTO } from "../../../objects/class/show/show.interface"
import { AllShowPageData, AllShowPageDTO } from "./interface"

export const allShowPageMapper = (data: AllShowPageDTO): AllShowPageData => {
    return {
        entities: data.response.data.map((result: ShowDTO) => new Show(result)),
        total: data.response.total
    }
}
