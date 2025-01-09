import { CityDTO } from "../../objects/class/city/city.interface";
import { ClubDTO } from "../../objects/class/club/club.interface";
import { ComedianDTO } from "../../objects/class/comedian/comedian.interface";

export interface HomePageDTO {
    cities: CityDTO[];
    comedians: ComedianDTO[];
    clubs: ClubDTO[]
}

export interface HomePageDataResponse { response: HomePageDTO }
