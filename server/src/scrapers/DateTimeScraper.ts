import Scrapable from "../types/scrapable.interface.js";
import { ElementScaper } from "./ElementScaper.js";
import { providedStringPromise, runTasks } from "../util/types/promiseUtil.js";
import { ScrapingConfig } from "../classes/ScrapingConfig.js";

export class DateTimeScraper {
  private scrapingConfig: ScrapingConfig;
  private elementScraper = new ElementScaper();

  constructor(scrapingConfig: ScrapingConfig) {
    this.scrapingConfig = scrapingConfig
  }

  getShowTime = async (showComponent: Scrapable) => {
    return this.elementScraper.getTextContent(showComponent, this.scrapingConfig.timeSelector)
  }

  getShowDate = async (showComponent: Scrapable) => {
    return this.elementScraper.getTextContent(showComponent, this.scrapingConfig.dateSelector)
  }

  getShowDateTime = async (showComponent: Scrapable): Promise<string>  => {
    return this.elementScraper.getTextContent(showComponent, this.scrapingConfig.dateTimeSelector)
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
    return this.scrapingConfig.dateTimeSelector ? this.getShowDateTime(showComponent)  : this.combineDateAndTime(showComponent, date)
  }

}
