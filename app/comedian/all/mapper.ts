import { Comedian } from "../../../objects/class/comedian/Comedian"
import { ComedianDTO } from "../../../objects/class/comedian/comedian.interface"
import { AllComedianPageData, AllComedianPageDTO } from "./interface"

export const allComedianPaegDataMapper = (data: AllComedianPageDTO): AllComedianPageData => {
    return {
        entities: data.response.data.map((result: ComedianDTO) => new Comedian(result)),
        total: data.response.total
    }
}
