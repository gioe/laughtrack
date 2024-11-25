import { DEFAULT, MapWithDefault } from "../class/map/MapWithDefault";

export enum QueryProperty {
    Direction = 'direction',
    Size = 'size',
    Page = 'page',
    Sort = 'sort_by',
    Query = 'query',
    Params = 'params',
    Tags = 'tags',
}

export const allQueryProperties = [
    QueryProperty.Direction.valueOf(),
    QueryProperty.Size.valueOf(),
    QueryProperty.Sort.valueOf(),
    QueryProperty.Query.valueOf(),
    QueryProperty.Page.valueOf(),
];

export const queryPropertyDefaultMap = new MapWithDefault<string, string>([
    [QueryProperty.Page, "0"],
    [QueryProperty.Size, "10"],
    [QueryProperty.Query, ""],
    [QueryProperty.Direction, "asc"],
    [DEFAULT, 'Unknown error']
]);
