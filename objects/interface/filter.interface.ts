export interface Selectable {
    id: number;
    name: string;
    selected: boolean;
}

export interface FilterSection {
    id: number;
    value: string;
    name: string;
    options: Selectable[];
}
