import {
    containsTimeRange,
    containsTimeValue,
    getMeridiemByRegex,
    getTimeByRegex,
} from "../../../util/primatives/timeUtil";

export class TimeContainer {
    timeString: string;
    hourString: string;
    hour: number;
    minutes: number;

    constructor(inputString: string) {
        this.timeString = inputString;

        if (containsTimeRange(inputString)) {
            this.timeString = inputString.split("-")[0];
        }

        if (!containsTimeValue(this.timeString)) {
            this.timeString = this.timeString.trimEnd() + ":00PM";
        }

        const timeValue = getTimeByRegex(this.timeString);
        const meridiem = getMeridiemByRegex(this.timeString).toUpperCase();

        this.timeString = timeValue;

        let hours = timeValue.split(":")[0];
        const minutes = timeValue.split(":")[1];

        this.hourString = " " + hours;

        if (parseInt(hours) == 12) {
            hours = "00";
        }

        this.hour = parseInt(hours) + (meridiem == "PM" ? 12 : 0);
        this.minutes = parseInt(minutes);
    }

    getHours = (): number => {
        return this.hour;
    };

    getMinutes = (): number => {
        return this.minutes;
    };

    getSeconds = (): number => {
        return 0;
    };

    getTimeString = (): string => {
        return this.timeString;
    };

    getHourString = (): string => {
        return this.hourString;
    };
}
