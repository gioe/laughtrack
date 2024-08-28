import { Club } from "../interfaces/club.interface.js";
import { Comedian } from "../interfaces/comedian.interface.js";

export type CreateShowDTO = {
    clubId: string;
    dateTime: Date;
    ticketLink: string;
    comedians: Comedian[];
    club: Club;
}

export type FilterShowsDTO = {
    isDeleted?: boolean
    includeDeleted?: boolean
}