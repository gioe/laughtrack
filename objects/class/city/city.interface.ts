import {
    DatabaseIdentifiable
} from "../../interface";

// Client
export interface CityInterface extends DatabaseIdentifiable {
    name: string;
}

// DB
export interface CityDTO {
    id: number;
    name: string;
    value?: string;
    displayName?: string;

}
