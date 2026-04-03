export enum SortParamValue {
    NameAsc = "name_asc",
    NameDesc = "name_desc",
    ActivityAsc = "activity_asc",
    ActivityDesc = "activity_desc",
    DateAsc = "date_asc",
    DateDesc = "date_desc",
    PriceAsc = "price_asc",
    PriceDesc = "price_desc",
    PopularityAsc = "popularity_asc",
    PopularityDesc = "popularity_desc",
    TotalShowsAsc = "total_shows_asc",
    TotalShowsDesc = "total_shows_desc",
    ShowCountDesc = "show_count_desc",
    ShowCountAsc = "show_count_asc",
    InsertedAtDesc = "inserted_at_desc",
    InsertedAtAsc = "inserted_at_asc",
}

export const allSortOptions = [
    SortParamValue.NameAsc.valueOf(),
    SortParamValue.NameDesc.valueOf(),
    SortParamValue.ActivityAsc.valueOf(),
    SortParamValue.ActivityDesc.valueOf(),
    SortParamValue.DateAsc.valueOf(),
    SortParamValue.DateDesc.valueOf(),
    SortParamValue.PriceAsc.valueOf(),
    SortParamValue.PriceDesc.valueOf(),
    SortParamValue.PopularityAsc.valueOf(),
    SortParamValue.PopularityDesc.valueOf(),
    SortParamValue.TotalShowsAsc.valueOf(),
    SortParamValue.TotalShowsDesc.valueOf(),
    SortParamValue.ShowCountDesc.valueOf(),
    SortParamValue.ShowCountAsc.valueOf(),
    SortParamValue.InsertedAtDesc.valueOf(),
    SortParamValue.InsertedAtAsc.valueOf(),
];

export const adminSortOptions = [
    SortParamValue.InsertedAtDesc.valueOf(),
    SortParamValue.InsertedAtAsc.valueOf(),
];
