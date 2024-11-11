export enum EntityType {
    Club = "club",
    Show = "show",
    Comedian = "comedian",
}

export enum UserRole {
    Admin = "admin",
    User = "user",
    Comedian = "comedian",
}

export enum URLParam {
    Sort = "sort",
    Query = "query",
    Page = "page",
    Rows = "rows",
    City = "city",
    StartDate = "startDate",
    EndDate = "endDate"
}

export enum SortParamValue {
    AlphabeticalAscending = 'alphabetical_asc',
    AlphabeticalDescending = 'alphabetical_desc',
    DateAscending = 'date_ascending',
    DateDescending = 'date_descending',
    PopularityAscending = 'popularity_asc',
    PopularityDescending = 'popularity_desc',
    PriceAscending = 'price_asc',
    PriceDescending = 'price_desc',
    ScrapeDateAscending = 'scrapedate_asc',
    ScrapeDateDescending = 'scrapedate_desc'
}

export enum ComedyClub {
    ComedyCellarNewYork = "Comedy Cellar New York",
    NewYorkComedyClubEastVillage = "New York Comedy Club East Village",
    NewYorkComedyClubUpperWestSide = "New York Comedy Club Upper West Side",
    NewYorkComedyClubMidtown = "New York Comedy Club Midtown",
    TheStand = "The Stand",
    TheGrislyPear = "The Grisly Pear",
    TheTinyCupboard = "The Tiny Cupboard",
    UnionHall = "Union Hall",
    WilliamsburgComedyClub = "Williamsburg Comedy Club",
    Rodneys = "Rodney’s",
    EastvilleComedyClubBrooklyn = "Eastville Comedy Club Brooklyn",
    ComedyVillage = "Comedy Village",
    Caveat = "Caveat",
    WestSideComedyClub = "West Side Comedy Club"
}

export enum SocialMedia {
    Instagram = "Instagram",
    Facebook = "Facebook",
    Twitter = "Twitter",
    TikTok = "TikTok",
    YouTube = "Youtube"
}
