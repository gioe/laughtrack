import puppeteer from "puppeteer";
import { ElementScaper } from "./ElementScaper.js";
import { providedStringPromise, runTasks } from "../util/types/promiseUtil.js";
import { normalizeDateTime } from "../util/types/dateTimeUtil.js";
import { Club } from "../classes/Club.js";

export class DateTimeScraper {
  private club: Club;
  private elementScraper = new ElementScaper();

  constructor(
    club: Club,
  ) {
    this.club = club
  }

  getShowTime = async (showComponent: puppeteer.ElementHandle<Element> | puppeteer.Page) => {
    return this.elementScraper.getTextContentFrom(showComponent, this.club.showConfig.timeSelector)
  }

  getShowDate = async (showComponent: puppeteer.ElementHandle<Element> | puppeteer.Page) => {
    return this.elementScraper.getTextContentFrom(showComponent, this.club.showConfig.dateSelector)
  }

  getShowDateTime = async (showComponent: puppeteer.ElementHandle<Element> | puppeteer.Page) => {
    return this.elementScraper.getTextContentFrom(showComponent, this.club.showConfig.dateTimeSelector)
    .then((datetime: string) => normalizeDateTime(datetime, this.club.showConfig))
  }

  combineDateAndTime = async (showComponent: puppeteer.ElementHandle<Element> | puppeteer.Page,
     date?: string) => {
    const dateTask = date ? providedStringPromise(date) : this.getShowDate(showComponent)
    const timeTask = this.getShowTime(showComponent)
    
    return runTasks([dateTask, timeTask])
    .then((scrapedValues: string[]) => {
      if (scrapedValues.length == 0) return ''
      const dateTime = scrapedValues[0] + ' ' + scrapedValues[1]
      return normalizeDateTime(dateTime, this.club.showConfig)
    })

  }

  getShowDateTimeJob = async (showComponent: puppeteer.ElementHandle<Element> | puppeteer.Page,
    date?: string) => {
    return this.club.showConfig.dateTimeSelector ? this.getShowDateTime(showComponent)  : this.combineDateAndTime(showComponent, date)
  }

}
