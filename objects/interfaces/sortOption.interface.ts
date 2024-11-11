import { SortParamValue } from "../../util/enum";

export interface SortOptionInterface {
    name: string;
    value: SortParamValue;
    default?: boolean
}
