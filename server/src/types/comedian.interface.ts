import { Show } from "./show.interface.js";
import { Storable } from "./storable.interface.js";

export interface ComedianInterface extends Storable { 
    name: string;
    website: string;
    shows: Show[]
}