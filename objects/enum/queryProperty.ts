import { DEFAULT, MapWithDefault } from "../class/map/MapWithDefault";

export enum QueryProperty {
    Direction = 'direction',
    Size = 'size',
    Page = 'page',
    Sort = 'sort_by',
    Query = 'query',
    Comedian = 'comedian',
    Club = 'club',
    Params = 'params',
    Tags = 'tags',
    Filters = 'filters',
    City = 'city',
    FromDate = 'from_date',
    ToDate = 'to_date'
}

export const allQueryProperties = [
    QueryProperty.Direction.valueOf(),
    QueryProperty.Size.valueOf(),
    QueryProperty.Sort.valueOf(),
    QueryProperty.Query.valueOf(),
    QueryProperty.Page.valueOf(),
    QueryProperty.Filters.valueOf(),
    QueryProperty.City.valueOf(),
    QueryProperty.Comedian.valueOf(),
    QueryProperty.Club.valueOf(),
];

export const DEFAULT_ERROR = 'Unknown error'

export const queryPropertyDefaultMap = new MapWithDefault<string, string>([
    [QueryProperty.Page, "0"],
    [QueryProperty.Size, "10"],
    [QueryProperty.Query, ""],
    [QueryProperty.Direction, "asc"],
    [QueryProperty.Sort, "name"],
    [QueryProperty.City, ""],
    [QueryProperty.Comedian, ""],
    [QueryProperty.Club, ""],
    [DEFAULT, DEFAULT_ERROR]
]);

