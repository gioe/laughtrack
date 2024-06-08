import { Comedian } from "./comedian.interface.js";

export interface Show {
    dateTime: string;
    timeZone: string;
    name: string;
    comedians: Comedian[];
    ticketLink: string;
}
