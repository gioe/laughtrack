import { determineDate, determineMonth, determineYear, normalizeDateString } from  "../../../util/primatives/dateUtil";

// Used for cases where the string value is a valid string, but doesn't contain a year so the DateConstructor
// defaults to 2001 instead of the current year;
const DEFAULT_YEAR = 2001;

export class DateContainer {

  dateString: string;
  dateObject: Date;

  constructor(dateString: string, timeString: string) {
    const separatedDateString = dateString.split(timeString)[0]
    this.dateString = normalizeDateString(separatedDateString)
    this.dateObject = new Date(this.dateString);
  }

  getYear = (): number => {
    if (isNaN(this.dateObject.getTime())) {
      return determineYear(this.getMonth()) 
    } else {
      const year = this.dateObject.getUTCFullYear();
      return year == DEFAULT_YEAR ? new Date().getUTCFullYear() : year
    }
  }

  getMonth = (): number => {
    return isNaN(this.dateObject.getTime()) ? determineMonth(this.dateString) : this.dateObject.getUTCMonth();
  }

  getDate = (): number => {
    if (isNaN(this.dateObject.getTime())) {
      const year = this.getYear().toString()
      const cleanedString =  this.dateString.replaceAll(year, "")
      return determineDate(cleanedString) 
    } else {
      return this.dateObject.getUTCDate();
    }
  }

  getDateString = (): string => {
    return this.dateString;
  }

}