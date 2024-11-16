import { Comedian } from "../../../objects/class/comedian/Comedian"
import { ComedianDetailDTO, ComedianDetailPageData } from "./interface"

export const comedianDetailPageMapper = (data: ComedianDetailDTO): ComedianDetailPageData => {
    return {
        entity: new Comedian(data.response.data),
        total: data.response.total
    }
}
