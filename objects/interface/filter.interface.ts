import { Selectable } from "./selectable.interface";

export interface FilterSection {
    id: number;
    value: string;
    displayName: string;
    options: Selectable[];
}
