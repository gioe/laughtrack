import { determineDay, determineMonth, determineYear, normalizeDateString } from "../../util/dateUtil.js";
import { ScrapingConfig } from "../models/ScrapingConfig.js";

// Used for cases where the string value is a valid string, but doesn't contain a year so the DateConstructor
// defaults to 2001 instead of the current year;
const DEFAULT_YEAR = 2001;

export class DateContainer {

  dateString: string = "";
  dateObject: Date;

  constructor(dateString: string,
    config: ScrapingConfig) {
    this.dateString = normalizeDateString(dateString, config);
    this.dateObject = new Date(this.dateString);
  }

  getYear = (): number => {
    if (isNaN(this.dateObject.getTime())) {
      return determineYear(this.getMonth()) 
    } else {
      const year = this.dateObject.getFullYear();
      return year == DEFAULT_YEAR ? new Date().getFullYear() : year
    }
  }

  getMonth = (): number => {
    return isNaN(this.dateObject.getTime()) ?  determineMonth(this.dateString) : this.dateObject.getMonth();
  }

  getDay = (): number => {
    return isNaN(this.dateObject.getTime()) ? determineDay(this.dateString) : this.dateObject.getDate();
  }

}