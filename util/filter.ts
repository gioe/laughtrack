import { Filter } from "../types/filter";

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
