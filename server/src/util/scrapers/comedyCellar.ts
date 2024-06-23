import puppeteer from 'puppeteer';
import { HTMLConfigurable } from "../../types/configs.interface.js";
import { getPropertyOfElements, getTextContent } from '../html/element.js';
import { addDelay, combineDateAndTime } from '../dateTime.js';
import { Show } from '../../types/show.interface.js';
import { Scraper } from '../../types/scraper.interface.js';
import { Club } from '../../types/club.interface.js';
import { combineWebsite } from '../website.js';
import { writeToFirestore } from '../storage/fireStore.js';
import { upsertComedian } from "../string/arrayUtil.js";
import { FIRESTORE_COLLECTIONS } from '../../constants/firestore.js';
import { Comedian } from '../../classes/Comedian.js';

export class ComedyCellarScaper implements Scraper {

  private scrapedComedians: Comedian[];

  private club: Club;

  public constructor(club: Club) {
    this.club = club
    this.scrapedComedians = [];
  }

  private htmlConfig() {
    return (this.club as HTMLConfigurable).htmlConfig;
  }

  private baseWebsite() {
    return this.club.baseWebsite
  }

  private scrapedWebsite() {
    return this.club.scrapedWebsite
  }

  private upsertScrapedComedian = (comedian: Comedian) => {
   upsertComedian(this.scrapedComedians, comedian)
  }

  private storeData = () => {
    this.scrapedComedians.forEach(comedian => {
      writeToFirestore(FIRESTORE_COLLECTIONS.comedians, comedian)
    })
  }

  scrape = async (page: puppeteer.Page) => {
    console.log(`Scraping ${this.scrapedWebsite()}`)
    const startTime = Date.now();

    await page.goto(this.scrapedWebsite())

    // Get all dates in the DOM since we assume we'll have to loop through them
    const dates = await page.$$eval(this.htmlConfig().allDateOptionsSelector, getPropertyOfElements, "value")

    for (let i = 0; i < dates.length - 1; i++) {

      // Get all the divs that represent a single show
      const showDivs = await page.$$(this.htmlConfig().allShowsSelector);

      for (const showDiv of showDivs) {
        const show = await this.scrapeShowDivForShowInfo(showDiv, dates[i]);
        const comedians = await this.scrapeShowDivForComedians(showDiv)

        for (const comedian of comedians) {
          comedian.addShows([show])
          this.upsertScrapedComedian(comedian)
        }

      }

      await page.select(this.htmlConfig().dateMenuSelector, dates[i + 1]);

      await addDelay(100);
    }

    if (this.scrapedComedians.length > 0) {
      this.storeData();
    } else {
      console.warn(`No comedians scraped from  for ${this.baseWebsite()}`)
    }

    const finishTime = Date.now();

    console.log(`It took ${finishTime - startTime} ms to complete scraping ${this.baseWebsite()}`)

  }


  scrapeShowDivForShowInfo = async (showDiv: puppeteer.ElementHandle<Element>, dateString: string): Promise<Show> => {
    const timeString = await showDiv.$eval(this.htmlConfig().selectedTimeSelector, getTextContent)
    const ticketLinkDivs = await showDiv.$$eval(this.htmlConfig().ticketLinkSelector, getPropertyOfElements, "href")
    const name = await showDiv.$eval(this.htmlConfig().selectedOptionalShowNameSelector, getTextContent)

    return {
      dateTime: combineDateAndTime(dateString, timeString ?? ""),
      name,
      ticketLink: combineWebsite(this.baseWebsite(), ticketLinkDivs),
      clubName: this.club.name,
      clubWebsite: this.club.scrapedWebsite,
    } as Show
  }

  scrapeShowDivForComedians = async (showDiv: puppeteer.ElementHandle<Element>) => {
    const comedianDivList = await showDiv.$$(this.htmlConfig().setContentSelector);
    const scrapedComedians: Comedian[] = []
   
    for (const comedianDiv of comedianDivList) {
      const scrapedComedian = await this.scrapeComedianDivForComedian(comedianDiv);
      scrapedComedians.push(scrapedComedian)
    }

    return scrapedComedians
  }

  scrapeComedianDivForComedian = async (element: puppeteer.ElementHandle<Element>): Promise<Comedian> => {
    const websites = await element.$$eval(this.htmlConfig().comedianWebsiteSelector, getPropertyOfElements, "href")
    const name = await element.$eval(this.htmlConfig().comedianNameSelector, getTextContent)
    return new Comedian(name ?? "", websites[0]);
  }

}
