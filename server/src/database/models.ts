/*
  Here we typed in simple models manually. But there are many tools out there
  for generating database models automatically, from an existing database.

  For example, schemats: https://github.com/sweetiq/schemats
*/

export interface ISchedule {
    id: number;
    club: IClub;
}

export interface ICity {
    id: number;
    name: string;
}

export interface IClub {
    id: number;
    name: string;
    popularity_score: any;
    base_url: string;
    schedule_page_url: string
    timezone: string;
    scraping_config: any;
    city: string;
    address: string
    latitude: number
    longitude: number
    image_name: string;
    shows: IShow[];
}

export interface IComedian {
    id: number;
    name: string;
    instagram_account: string;
    instagram_followers: number;
    tiktok_account: string;
    tiktok_followers: number;
    website: string;
    is_pseudonym: boolean;
    popularity_score: any;
    non_comedian: boolean;
}

export interface IShowComedian {
    id: number;
    show_id: number;
    comedian_id: number;
}

export interface IShow {
    id: number;
    club: IClub;
    date_time: Date;
    ticket_link: string;
    popularity_score: any;
    lineup: IComedian[];
}

export interface IUser {
    id: number;
    email: string;
    password: string;
    role: string;
}

export interface IComedianPopularityData {
    id: number;
    instagram_followers: number;
    tiktok_follwers: number;
    is_pseudonym: boolean;
    non_comedian: boolean;
}

export interface IShowSearchResult {
    id: number;
    date_time: Date;
    ticket_link: string;
    club_name: string;
    club_url: string;
    popularity_score: number;
    lineup: IComedian[];
    coordinates: ICoordinates[];
}

export interface ICoordinates {
    latitude: string;
    longitude: string;
}

export interface IShowPoularityScore {
    id: number;
    popularity_score: number;
}

export interface IShowPopularityData {
    id: number;
    scores: IPopularityScore[];
}

export interface IClubPopularityData {
    id: number;
    scores: IPopularityScore[];
}

export interface IPopularityScore {
    popularity_score: number
}

export interface ISocialData {
    instagram_account: string;
    instagram_followers: number;
    tiktok_account: string;
    tiktok_followers: number;
    website: string;
}

export interface IComedianDetails {
    id: number;
    name: string;
    social_data: ISocialData;
    dates: IShowDetails[]
}

export interface IShowDetails {
    show_id: number
    city: string;
    club_name: string;
    date_time: string;
    ticket_link: string;
    lineup: ILineupItem[]
}

export interface ILineupItem {
    id: number;
    name: string;
    popularity_score: number;
}

export interface IClubDetails {
    id: number;
    name: string;
    city: string;
    longitude: number;
    latitude: number;
    dates: IShowDetails[];
    base_url: string;
}