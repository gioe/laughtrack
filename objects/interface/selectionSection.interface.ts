import { Selectable } from "./selectable.interface";

export interface SelectionSection {
    id: number;
    value: string;
    display: string;
    options: Selectable[];
    handleSelection: (option: number) => void
    asParamValue: () => string[]
}
