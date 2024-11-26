import { Selectable } from "./selectable.interface";

export interface SelectionSection {
    id: number;
    value: string;
    displayName: string;
    options: Selectable[];
}
