export interface Selectable {
    id: number;
    displayName: string;
    selected: boolean;
    select: () => void;
}

export interface FilterSection {
    id: number;
    value: string;
    displayName: string;
    options: Selectable[];
}
