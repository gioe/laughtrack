import { DateRange, DateRangeInput } from "@/objects/interface";

export const getDateRangeFromParams = (input: DateRangeInput): DateRange => {
    const from = new Date(input.from ?? "");
    const to = new Date(input.to ?? "");

    return {
        from: isNaN(from.getTime()) ? undefined: from,
        to: isNaN(to.getTime()) ? undefined : to
    };
};
