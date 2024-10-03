import { Scrapable } from "../../common/interfaces/client/scrapable.interface.js";
import { ScrapingConfig } from "../../common/models/ScrapingConfig.js";
import { stringIsAValidDate } from "../../common/util/dateUtil.js";
import { providedStringPromise, runTasks } from "../../common/util/promiseUtil.js";
import { getTimeByRegex } from "../../common/util/timeUtil.js";
import { ScrapableScraper } from "./ScrapableScraper.js";

export class DateTimeScraper {
  private scrapingConfig: ScrapingConfig;
  private scraper = new ScrapableScraper();

  constructor(scrapingConfig: ScrapingConfig) {
    this.scrapingConfig = scrapingConfig
  }

  getShowTime = async (scrapable: Scrapable) => {
    return this.scraper.getTextContent(scrapable, this.scrapingConfig.timeSelector)
  }

  getShowDate = async (scrapable: Scrapable) => {
    return this.scraper.getTextContent(scrapable, this.scrapingConfig.dateSelector)
  }

  getShowDateTime = async (scrapable: Scrapable): Promise<string>  => {
    return this.scraper.getTextContent(scrapable, this.scrapingConfig.dateTimeSelector)
  }

  getShowTimeAndAppendDate = async (scrapable: Scrapable,
    date?: string): Promise<string> => {

   const dateTask = stringIsAValidDate(date ?? "") ? providedStringPromise(date ?? "") : this.getShowDate(scrapable)
   const timeTask = this.getShowTime(scrapable)
 
   return runTasks([dateTask, timeTask])
   .then((scrapedValues: string[]) => {
     if (scrapedValues.length == 0) return ""
     return scrapedValues[0] + ' ' + scrapedValues[1]
   })
 }

 getShowDateAndShowTime = async (scrapable: Scrapable): Promise<string> => {

  const dateTask = this.getShowDate(scrapable)
    const timeTask = this.getShowTime(scrapable).then((timeString: string) => getTimeByRegex(timeString))
  
    return runTasks([dateTask, timeTask])
    .then((scrapedValues: string[]) => {
      if (scrapedValues.length == 0) return ""
      return scrapedValues[0] + ' ' + scrapedValues[1]
    })
  }

  getShowDateTimeTask = async (scrapable: Scrapable,
    date?: string): Promise<string> => {
      if (this.scrapingConfig.dateTimeSelector !== undefined) {
       return this.getShowDateTime(scrapable) 
      } else if (this.scrapingConfig.timeSelector !== undefined && this.scrapingConfig.dateSelector !== undefined) {
        return this.getShowDateAndShowTime(scrapable) 
      }
      return this.getShowTimeAndAppendDate(scrapable, date)

  }

}
