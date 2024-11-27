import { CityDTO } from "../../objects/class/city/city.interface";
import { ComedianDTO } from "../../objects/class/comedian/comedian.interface";

export interface HomePageDTO {
    response: {
        cities: CityDTO[];
        comedians: ComedianDTO[];
    }
}
