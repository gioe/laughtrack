import { Club } from "../../../objects/class/club/Club"
import { ClubDetailPageData, ClubDetailDTO } from "./interface"

export const clubDetailPageMapper = (data: ClubDetailDTO): ClubDetailPageData => {
    return {
        entity: new Club(data.response.data),
        total: data.response.total
    }
}
