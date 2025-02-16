
export enum SortParamValue {
    Name = 'name',
    Date = 'date',
    Popularity = 'popularity',
    Activity = 'activity',
    Price = 'ticketPrice',
    ScrapeDate = 'scrapedate'
}

export const allSortOptions = [
    SortParamValue.Name.valueOf(),
    SortParamValue.Date.valueOf(),
    SortParamValue.Price.valueOf(),
    SortParamValue.Popularity.valueOf(),
    SortParamValue.Activity.valueOf()
]
