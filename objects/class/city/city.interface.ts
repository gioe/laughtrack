import {
    Identifiable
} from "../../interface";

// Client
export interface CityInterface extends Identifiable {
    name: string;
}

// DB
export interface CityDTO {
    id: number;
    name: string
}
