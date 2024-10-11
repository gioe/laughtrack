import { ScrapingConfig } from "../../../common/models/classes/ScrapingConfig.js";
import { normalizeDateString } from "../../../common/util/primatives/dateUtil.js";
import { getTimeByRegex, normalizeTimeString } from "../../../common/util/timeUtil.js";
import { DateContainer } from "./DateContainer.js";
import { TimeContainer } from "./TimeContainer.js";

const DEFAULT_DATE = "Sep 9 1989"
const DEFAULT_TIME = "10:00 PM"
export class DateTimeContainer {

  dateContainer: DateContainer;
  timeContainer: TimeContainer;

  constructor(dateTimeString: string, config: ScrapingConfig) {

    var providedString = dateTimeString;

    if (dateTimeString == undefined) {
      providedString = DEFAULT_DATE
    }

    var timeValue = getTimeByRegex(providedString);

    if (timeValue.length == 0) {
      timeValue = DEFAULT_TIME
      providedString = providedString + ' ' + timeValue
    }

    const dateString = providedString.split(timeValue)[0];
    const meridiem = providedString.split(timeValue)[1];
    const normalizedDateString = normalizeDateString(dateString, config)
    const normalizedTimeString = normalizeTimeString(timeValue, meridiem, config)

    this.dateContainer = new DateContainer(normalizedDateString)
    this.timeContainer = new TimeContainer(normalizedTimeString)
  }

  asDateObject = (): Date => {
    return new Date(this.dateContainer.getYear(),
      this.dateContainer.getMonth(),
      this.dateContainer.getDate(),
      this.timeContainer.getHours(),
      this.timeContainer.getMinutes(),
      this.timeContainer.getSeconds())
  }

  getYear = () => {
    return this.asDateObject().getFullYear();
  }

  getMonth = () => {
    return this.asDateObject().getMonth();
  }

  getDate = () => {
    return this.asDateObject().getDate();
  }

  getHours = () => {
    return this.asDateObject().getHours();
  }

  getMinutes = () => {
    return this.asDateObject().getMinutes();
  }

  getSeconds = () => {
    return this.asDateObject().getSeconds();
  }

  isValid = (): boolean => {
    return !isNaN(this.asDateObject().getTime())
  }

}