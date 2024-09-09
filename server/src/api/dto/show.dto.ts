import { ComedianInterface } from "../../common/interfaces/comedian.interface.js";

export type UpdateShowOutput = CreateShowOutput;
export type GetShowIdOutput = CreateShowOutput;
export type GetShowByIdDTO = CreateShowOutput;
export type GetShowDetailsOutput = UpdateShowDTO;

export type CreateShowDTO = {
    club_id: number;
    date_time: Date;
    ticket_link: string;
    comedians: ComedianInterface[];
}

export type CreateShowOutput = {
    id: number;
}

export type UpdateShowDTO = {
    id: number;
    club_id: string;
    date_time: Date;
    ticket_link: string;
}

export type GetShowByClubAndTimeDTO = {
    club_id: string;
    date_time: Date;
}

export type ShowExistenceDTO = {
    club_id: string;
    date_time: Date;
}
