
export type Filter<A> =
  | { kind: "Equals"; field: keyof A; val: A[keyof A] }
  | { kind: "Greater"; field: keyof A; val: A[keyof A] }
  | { kind: "Less"; field: keyof A; val: A[keyof A] }
  | { kind: "And"; a: Filter<A>; b: Filter<A> }
  | { kind: "Or"; a: Filter<A>; b: Filter<A> };