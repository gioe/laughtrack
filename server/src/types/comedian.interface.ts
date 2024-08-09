import { Show } from "../classes/Show.js";
import { Storable } from "./storable.interface.js";

export interface ComedianInterface extends Storable { 
    name: string;
    shows: Show[];
}