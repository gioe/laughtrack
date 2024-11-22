import { DateContainer } from "./DateContainer";
import { TimeContainer } from "./TimeContainer";

const DEFAULT_DATE = "1/1/90 8:00PM";

export class DateTimeContainer {
    dateContainer: DateContainer;
    timeContainer: TimeContainer;

    constructor(scrapedValues: string[], dateTimeSeparator?: string) {
        let fullString = scrapedValues.join();

        if (dateTimeSeparator) {
            fullString = fullString.replaceAll(dateTimeSeparator, " ");
        }

        if (scrapedValues.length == 0) {
            fullString = DEFAULT_DATE;
        }

        this.timeContainer = new TimeContainer(fullString);
        this.dateContainer = new DateContainer(
            fullString,
            this.timeContainer.getHourString(),
        );
    }

    asDateObject = (): Date => {
        return new Date(
            this.dateContainer.getYear(),
            this.dateContainer.getMonth(),
            this.dateContainer.getDate(),
            this.timeContainer.getHours(),
            this.timeContainer.getMinutes(),
            this.timeContainer.getSeconds(),
        );
    };

    getYear = () => {
        return this.asDateObject().getFullYear();
    };

    getMonth = () => {
        return this.asDateObject().getMonth();
    };

    getDate = () => {
        return this.asDateObject().getDate();
    };

    getHours = () => {
        return this.asDateObject().getHours();
    };

    getMinutes = () => {
        return this.asDateObject().getMinutes();
    };

    getSeconds = () => {
        return this.asDateObject().getSeconds();
    };

    isValid = (): boolean => {
        return !isNaN(this.asDateObject().getTime());
    };
}
