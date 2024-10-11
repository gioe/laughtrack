import { determineDate, determineMonth, determineYear } from"../../../common/util/primatives/dateUtil.js";

// Used for cases where the string value is a valid string, but doesn't contain a year so the DateConstructor
// defaults to 2001 instead of the current year;
const DEFAULT_YEAR = 2001;

export class DateContainer {

  dateString: string;
  dateObject: Date;

  constructor(dateString: string) {
    this.dateString = dateString
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
    return isNaN(this.dateObject.getTime()) ? determineMonth(this.dateString) : this.dateObject.getMonth();
  }

  getDate = (): number => {
    if (isNaN(this.dateObject.getTime())) {
      const year = this.getYear().toString()
      const cleanedString =  this.dateString.replaceAll(year, "")
      return determineDate(cleanedString) 
    } else {
      return this.dateObject.getDate();
    }

  }

}