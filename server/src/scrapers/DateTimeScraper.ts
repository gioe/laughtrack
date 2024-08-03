import { ElementScaper } from "./ElementScaper.js";
import { providedStringPromise, runTasks } from "../util/types/promiseUtil.js";
import { Club } from "../classes/Club.js";
import Scrapable from "../types/scrapable.interface.js";

export class DateTimeScraper {
  private club: Club;
  private elementScraper = new ElementScaper();

  constructor(
    club: Club,
  ) {
    this.club = club
  }

  getShowTime = async (showComponent: Scrapable) => {
    return this.elementScraper.getTextContentFrom(showComponent, this.club.showConfig.timeSelector)
  }

  getShowDate = async (showComponent: Scrapable) => {
    return this.elementScraper.getTextContentFrom(showComponent, this.club.showConfig.dateSelector)
  }

  getShowDateTime = async (showComponent: Scrapable): Promise<string>  => {
    return this.elementScraper.getTextContentFrom(showComponent, this.club.showConfig.dateTimeSelector)
  }

  combineDateAndTime = async (showComponent: Scrapable,
     date?: string): Promise<string> => {
    const dateTask = date ? providedStringPromise(date) : this.getShowDate(showComponent)
    const timeTask = this.getShowTime(showComponent)
  
    return runTasks([dateTask, timeTask])
    .then((scrapedValues: string[]) => {
      if (scrapedValues.length == 0) return ""
      const dateTime = scrapedValues[0] + ' ' + scrapedValues[1]
      return dateTime
    })

  }

  getShowDateTimeTask = async (showComponent: Scrapable,
    date?: string): Promise<string> => {
    return this.club.showConfig.dateTimeSelector ? this.getShowDateTime(showComponent)  : this.combineDateAndTime(showComponent, date)
  }

}
