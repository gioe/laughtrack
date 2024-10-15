import { DateContainer } from "./DateContainer.js";
import { TimeContainer } from "./TimeContainer.js";

const DEFAULT_STRING = "Friday January 1st, 1990 - 8:00PM"

export class DateTimeContainer {

  dateContainer: DateContainer;
  timeContainer: TimeContainer;

  constructor(scrapedValues: string[]) {    
    var fullString = scrapedValues.join()

    if (scrapedValues.length == 0) {
      fullString = DEFAULT_STRING
    }

    this.timeContainer = new TimeContainer(fullString)
    this.dateContainer = new DateContainer(fullString, this.timeContainer.getTimeString())

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