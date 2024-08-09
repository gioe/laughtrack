import { Comedian } from "../classes/Comedian.js";

export interface ComedianContainer {
    comedianArrays: Comedian[][];    
    nextPageLink: string;
}
