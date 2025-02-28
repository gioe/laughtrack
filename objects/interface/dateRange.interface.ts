export interface DateRangeInput {
    from: string | null;
    to: string | null;
}

export interface DateRange {
    from: Date | undefined;
    to?: Date | undefined;
}
