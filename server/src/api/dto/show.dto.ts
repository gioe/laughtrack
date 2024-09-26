import { ComedianInterface } from "../../common/interfaces/comedian.interface.js";

export type UpdateShowOutput = CreateShowOutput;
export type GetShowIdOutput = CreateShowOutput;
export type GetShowByIdDTO = CreateShowOutput;

export type GetShowDetailsOutput = {
    id: number;
    club_id: number;
    date_time: Date;
    ticket_link: string;
};

export type GetFilteredShowsRequest = {
    location: string;
    startDate: string;
    endDate: string;
};

export type GetFilteredShowsResponse = {
    show_id: number;
    date_time: Date;
    ticket_link: string;
    name: string;
    city: string;
    address: string;
};


export type CreateShowDTO = {
    clubId: number;
    dateTime: Date;
    ticketLink: string;
    comedians: ComedianInterface[];
}

export type CreateShowOutput = {
    id: number;
}

export type UpdateShowDTO = {
    id: number;
    clubId: string;
    dateTime: Date;
    ticketLink: string;
}

export type GetShowByClubAndTimeDTO = {
    clubId: string;
    dateTime: Date;
}

export type ShowExistenceDTO = {
    clubId: string;
    dateTime: Date;
}


export type ShowScore = {
    showId: number;
    score: number;
}