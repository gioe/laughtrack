import { getTimeByRegex } from "../../util/timeUtil.js";
import { ScrapingConfig } from "../models/ScrapingConfig.js";
import { DateContainer } from "./DateContainer.js";
import { TimeContainer } from "./TimeContainer.js";

export class DateTimeContainer  {

  dateContainer: DateContainer;
  timeContainer: TimeContainer;
  dateTimeString: string;

  constructor(dateTimeString: string,
    config: ScrapingConfig) {
    this.dateTimeString = dateTimeString
    const timeValue = getTimeByRegex(dateTimeString)
    this.dateContainer = new DateContainer(dateTimeString.split(timeValue)[0], config)
    this.timeContainer = new TimeContainer(timeValue + dateTimeString.split(timeValue)[1], config)
  }

asDateObject = (): Date => {       
    return new Date(this.dateContainer.getYear(), 
    this.dateContainer.getMonth(), 
    this.dateContainer.getDay(), 
    this.timeContainer.getHours(), 
    this.timeContainer.getMinutes(), 
    this.timeContainer.getSeconds())
}

isValid = (): boolean => {
  return !isNaN(this.asDateObject().getTime())
}

}