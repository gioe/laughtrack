import { IShowDetails } from "../../database/models.js";
import { ShowDetailsInterface } from "./show.interface.js";

export interface HomeSearchResultInterface {
    city: string;
    shows: ShowDetailsInterface[]
}
