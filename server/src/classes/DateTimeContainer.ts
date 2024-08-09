import DateTimeContainerInterface from "../types/dateTimeContainer.interface.js";
import { getTimeByRegex } from "../util/types/timeUtil.js";
import { DateContainer } from "./DateContainer.js";
import { ScrapingConfig } from "./ScrapingConfig.js";
import { TimeContainer } from "./TimeContainer.js";

export class DateTimeContainer implements DateTimeContainerInterface {

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
    // console.log(`Full string: ${this.dateTimeString}`)
    // console.log(`Year: ${this.dateContainer.getYear()}`)
    // console.log(`Month: ${this.dateContainer.getMonth()}`)
    // console.log(`Day: ${this.dateContainer.getDay()}`)
    // console.log(`Hour: ${this.timeContainer.getHours()}`)
    // console.log(`Minute: ${this.timeContainer.getMinutes()}`)
    // console.log(`Second: ${this.timeContainer.getSeconds()}`)
    

    // const dateObject = new Date(this.dateContainer.getYear(), 
    // this.dateContainer.getMonth(), 
    // this.dateContainer.getDay(), 
    // this.timeContainer.getHours(), 
    // this.timeContainer.getMinutes(), 
    // this.timeContainer.getSeconds())

    // console.log(`Object version: ${dateObject}`)
    
    return new Date(this.dateContainer.getYear(), 
    this.dateContainer.getMonth(), 
    this.dateContainer.getDay(), 
    this.timeContainer.getHours(), 
    this.timeContainer.getMinutes(), 
    this.timeContainer.getSeconds())
}

}