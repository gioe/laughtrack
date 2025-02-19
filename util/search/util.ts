import { DateRange, DateRangeInput } from "@/objects/interface";

export const getDateRangeFromParams = (input: DateRangeInput): DateRange => {
    console.log(`Input: ${input.from}`);
    const from = new Date(input.from ?? "");
    console.log(`From: ${from}`);
    const to = new Date(input.to ?? "");

    return {
        from: isNaN(from.getTime()) ? undefined: from,
        to: isNaN(to.getTime()) ? undefined : to
    };
};
