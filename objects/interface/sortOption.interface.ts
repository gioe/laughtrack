import { DirectionParamValue, SortParamValue } from "../enum";

export interface SortOptionInterface {
    name: string;
    value: SortParamValue;
    direction: DirectionParamValue,
}
