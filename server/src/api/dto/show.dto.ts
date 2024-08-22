import { CreateComedianDTO } from "./comedian.dto.js";

export type CreateShowDTO = {
    dateTime: Date;
    ticketLink: string;
    slug?: string;
    comedians?: CreateComedianDTO[]
}

export type FilterShowsDTO = {
    isDeleted?: boolean
    includeDeleted?: boolean
}