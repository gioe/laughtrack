import { DateRange } from "@/ui/components/calendar";
import {
    removeNonNumbers,
} from "./stringUtil";
import { datesAreToday, datesAreTomorrow } from "@/util/dateUtil";
import { format, isToday, isTomorrow } from "date-fns";

export const determineDate = (dateString: string): number => {
    const numberString = removeNonNumbers(dateString);
    return Number(numberString);
};

export const formatDateRange = (range: DateRange): string => {
    const { from, to } = range;

    if (!to) {
        return format(from, "LLL dd, yyyy");
    }

    if (datesAreToday(from, to)) {
        return "Today";
    }

    if (datesAreTomorrow(from, to)) {
        return "Tomorrow";
    }

    const formatStartDate = (): string => {
        if (isToday(from)) return "Today";
        if (isTomorrow(from)) return "Tomorrow";
        return format(from, "LLL d, yyyy");
    };

    return `${formatStartDate()} - ${format(to, "LLL d, yyyy")}`;
};
