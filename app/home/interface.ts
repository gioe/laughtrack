import { Comedian } from "../../objects/class/comedian/Comedian";
import { ComedianDTO } from "../../objects/class/comedian/comedian.interface";
import { CityDTO, CityInterface } from "../../objects/interface/city.interface";

export interface HomePageDTO {
    response: {
        cities: CityDTO[];
        comedians: ComedianDTO[];
    }
}

export interface HomePageData {
    cities: CityInterface[];
    comedians: Comedian[];
}
