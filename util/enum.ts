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
    AlphabeticalAscending = 'Name_Asc',
    AlphabeticalDescending = 'Name_Desc',
    DateAscending = 'Date_Asc',
    DateDescending = 'Date_Desc',
    PopularityAscending = 'Popularity_Asc',
    PopularityDescending = 'Popularity_Desc',
    PriceAscending = 'Price_Asc',
    PriceDescending = 'Price_Desc',
    ScrapeDateAscending = 'ScrapeDate_Asc',
    ScrapeDateDescending = 'ScrapeDate_Desc'
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
