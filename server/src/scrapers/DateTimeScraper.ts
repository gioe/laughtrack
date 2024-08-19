import { ScrapableScraper } from "./ScrapableScraper.js";
import { providedStringPromise, runTasks } from "../util/types/promiseUtil.js";
import { ScrapingConfig } from "../classes/ScrapingConfig.js";
import { stringIsAValidDate } from "../util/types/dateUtil.js";
import { Scrapable } from "../types/scrapable.interface.js";

export class DateTimeScraper {
  private scrapingConfig: ScrapingConfig;
  private scraper = new ScrapableScraper();

  constructor(scrapingConfig: ScrapingConfig) {
    this.scrapingConfig = scrapingConfig
  }

  getShowTime = async (scrapable: Scrapable) => {
    return this.scraper.getTextContent(scrapable, this.scrapingConfig.showTimeSelector)
  }

  getShowDate = async (scrapable: Scrapable) => {
    return this.scraper.getTextContent(scrapable, this.scrapingConfig.dateSelector)
  }

  getShowDateTime = async (scrapable: Scrapable): Promise<string>  => {
    return this.scraper.getTextContent(scrapable, this.scrapingConfig.dateTimeSelector)
  }

  combineDateAndTime = async (scrapable: Scrapable,
     date?: string): Promise<string> => {
    const dateTask = stringIsAValidDate(date ?? "") ? providedStringPromise(date ?? "") : this.getShowDate(scrapable)
    
    const timeTask = this.getShowTime(scrapable)
  
    return runTasks([dateTask, timeTask])
    .then((scrapedValues: string[]) => {
      if (scrapedValues.length == 0) return ""
      return scrapedValues[0] + ' ' + scrapedValues[1]
    })

  }

  getShowDateTimeTask = async (scrapable: Scrapable,
    date?: string): Promise<string> => {
    
    return this.scrapingConfig.dateTimeSelector ? this.getShowDateTime(scrapable) : this.combineDateAndTime(scrapable, date)
  }

}
