import { DateRange, DateRangeInput } from "@/objects/interface";

type DateRangeParam = DateRangeInput | DateRange;

const parseDateParam = (value: string | Date | null | undefined) => {
    if (value instanceof Date) return value;
    return new Date(value ?? "");
};

export const getDateRangeFromParams = (input: DateRangeParam): DateRange => {
    const from = parseDateParam(input.from);
    const to = parseDateParam(input.to);

    return {
        from: isNaN(from.getTime()) ? undefined : from,
        to: isNaN(to.getTime()) ? undefined : to,
    };
};
