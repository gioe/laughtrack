export enum QueryProperty {
    Direction = 'direction',
    Size = 'size',
    Page = 'page',
    Sort = 'sort_by'
}

export const allQueryProperties = [
    QueryProperty.Direction.valueOf(),
    QueryProperty.Size.valueOf(),
    QueryProperty.Sort.valueOf(),
    QueryProperty.Page.valueOf(),
];
