import { Comedian } from "../../objects/class/comedian/Comedian"
import { ComedianDTO } from "../../objects/class/comedian/comedian.interface"
import { HomePageData, HomePageDTO } from "./interface"

export const homePageDataMapper = (data: HomePageDTO): HomePageData => {
    return {
        cities: data.response.cities,
        comedians: data.response.comedians.map((dto: ComedianDTO) => new Comedian(dto))
    }
}
