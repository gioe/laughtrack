import { Club } from "./club.interface.js";
import { Comedian } from "./comedian.interface.js";

export interface Show {
    club: Club;
    dateTime: string;
    name: string;
    comedians: Comedian[];
}
