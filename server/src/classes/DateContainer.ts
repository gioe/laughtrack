import DateContainerInterface from "../types/dateContainer.interface.js";
import { ShowHTMLConfiguration } from "../types/htmlconfigurable.interface.js";
import { buildDateObjectIfPossible, determineDay, determineMonth, determineYear, normalizeDateString } from "../util/types/dateUtil.js";

export class DateContainer implements DateContainerInterface {

  config: ShowHTMLConfiguration;
  dateString: string = "";
  dateObject?: Date;

  constructor(dateString: string,
    config: ShowHTMLConfiguration) {
    this.config = config;
    this.dateString = normalizeDateString(dateString, config);
    this.dateObject = buildDateObjectIfPossible(dateString);
  }

  getDay = (): number => {
    return this.dateObject ? this.dateObject.getDate() : determineDay(this.dateString);
  }

  getMonth = (): number => {
    return this.dateObject ? this.dateObject.getMonth() + 1 : determineMonth(this.dateString) + 1;
  }

  getYear = (): number => {
    return this.dateObject ? this.dateObject.getFullYear() : determineYear(this.getMonth());
  }

}