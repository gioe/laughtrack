import { Club } from "../../../objects/class/club/Club"
import { ClubDTO } from "../../../objects/class/club/club.interface"
import { AllClubPageDTO, AllClubPageData } from "./interface"

export const allClubPageMapper = (data: AllClubPageDTO): AllClubPageData => {
    return {
        entities: data.response.data.map((result: ClubDTO) => new Club(result)),
        total: data.response.total
    }
}
