import DateTimeContainerInterface from "../types/dateTimeContainer.interface.js";
import { ShowHTMLConfiguration } from "../types/htmlconfigurable.interface.js";
import { getTimeByRegex } from "../util/types/timeUtil.js";
import { DateContainer } from "./DateContainer.js";
import { TimeContainer } from "./TimeContainer.js";

export class DateTimeContainer implements DateTimeContainerInterface {

  dateContainer: DateContainer;
  timeContainer: TimeContainer;

  constructor(dateTimeString: string,
    config: ShowHTMLConfiguration) {
    const timeValue = getTimeByRegex(dateTimeString)
    this.dateContainer = new DateContainer(dateTimeString.split(timeValue)[0], config)
    this.timeContainer = new TimeContainer(timeValue + dateTimeString.split(timeValue)[1], config)
  }

asDateObject = (): Date => {
    return new Date(this.dateContainer.getYear(), 
    this.dateContainer.getMonth(), 
    this.dateContainer.getDay(), 
    this.timeContainer.getHour(), 
    this.timeContainer.getMinute(), 
    this.timeContainer.getSeconds())
}

}