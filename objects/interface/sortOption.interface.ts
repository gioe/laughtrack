import { SortParamValue } from "../enum";

export interface SortOptionInterface {
    name: string;
    value: SortParamValue;
    default?: boolean
}
