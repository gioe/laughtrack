export interface DateRangeInput {
    from: string | null;
    to: string | null;
}

export interface DateRange {
    from: Date;
    to?: Date;
}

export interface DistanceData {
    distance: string | null;
    zipCode: string | null;
}

export const getDateRangeFromParams = (input: DateRangeInput): DateRange | undefined => {

    const from = new Date(input.from ?? "");
    const to = new Date(input.to ?? "");

    return {
        from: isNaN(from.getTime()) ? new Date() : from,
        to: isNaN(to.getTime()) ? undefined : to
    };
};
