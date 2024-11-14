
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

export const allSortOptions = [
    SortParamValue.AlphabeticalAscending,
    SortParamValue.AlphabeticalDescending,
    SortParamValue.DateAscending,
    SortParamValue.DateDescending,
    SortParamValue.PopularityAscending,
    SortParamValue.PopularityDescending,
    SortParamValue.PriceAscending,
    SortParamValue.PriceDescending,
    SortParamValue.ScrapeDateAscending,
    SortParamValue.ScrapeDateDescending,
]
