import { DirectionParamValue, QueryProperty, SortParamValue } from "@/objects/enum";
import { Filter } from "../../objects/type/filter";
import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { SortOptionInterface } from "@/objects/interface";


export const equals = <A, K extends keyof A>(
    field: K,
    val: A[K],
): Filter<A> => ({
    kind: "Equals",
    field,
    val,
});
export const greater = <A, K extends keyof A>(
    field: K,
    val: A[K],
): Filter<A> => ({
    kind: "Greater",
    field,
    val,
});
export const less = <A, K extends keyof A>(field: K, val: A[K]): Filter<A> => ({
    kind: "Less",
    field,
    val,
});
export const and = <A>(a: Filter<A>, b: Filter<A>): Filter<A> => ({
    kind: "And",
    a,
    b,
});
export const or = <A>(a: Filter<A>, b: Filter<A>): Filter<A> => ({
    kind: "Or",
    a,
    b,
});

export const getDefaultSortingOption = (sortOptions: SortOptionInterface[], paramsHelper: SearchParamsHelper) => {
    return sortOptions.find(
        (value) =>
            value.value == paramsHelper.getParamValue(QueryProperty.Sort) &&
            value.direction ==
            paramsHelper.getParamValue(QueryProperty.Direction),
    ) ?? {
        name: "",
        value: SortParamValue.Date,
        direction: DirectionParamValue.Ascending
    } as SortOptionInterface

}
