import { ComedianInterface } from "../../common/interfaces/comedian.interface.js";

export type GetShowDetailsOutput = {
    id: number;
    club_id: number;
    date_time: Date;
    ticket_link: string;
    popularity_score: number;
};

export type UpdateShowScoreDTO = {
    id: number;
    score: number;
}

export type GetFilteredShowsRequest = {
    location: string;
    startDate: string;
    endDate: string;
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

export type ShowScore = {
    showId: number;
    score: number;
}