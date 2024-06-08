import puppeteer from 'puppeteer';
import { HTMLConfigurable } from "../../types/configs.interface.js";
import { getPropertyOfElements, getTextContent } from '../html/element.js';
import { writeToFirestore } from '../../util/storage/dataStore.js';
import { addDelay, combineDateAndTimeStrings } from '../dateTime.js';
import { Show } from '../../types/show.interface.js';
import { Scraper } from '../../types/scraper.interface.js';
import { Comedian } from '../../types/comedian.interface.js';
import { Club } from '../../types/club.interface.js';
import { combineWebsite } from '../website.js';

export class ComedyCellarScaper implements Scraper {
  private club: Club;

  public constructor(club: Club) {
    this.club = club
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

  scrape = async (page: puppeteer.Page) => {
    console.log(`Scraping ${this.scrapedWebsite()}`)
    await page.goto(this.scrapedWebsite())

    // Get the date do
    const dates = await page.$$eval(this.htmlConfig().allDateOptionsSelector, getPropertyOfElements, "value")

    const scrapedShows: Show[] = [];

    for (let i = 0; i < dates.length - 1; i++) {   
      const shows = await this.scrapeShowsOnDate(dates[i], page);    
      scrapedShows.push(...shows);

      await page.select(this.htmlConfig().dateMenuSelector, dates[i+1]);

      await addDelay(100);
    }

    if (scrapedShows.length == 0) {
      console.log(`Scraper returned no shows for ${this.scrapedWebsite}`)
    } else {
      writeToFirestore(scrapedShows);
    }
    
  }
  

private scrapeShowsOnDate = async (dateString: string, page: puppeteer.Page) => {
    const showDivs = await page.$$(this.htmlConfig().allShowsSelector);

    const shows: Show[] = [];

    for (const showDiv of showDivs) {
      const show = await this.scrapeShow(showDiv, dateString);
      shows.push(show);
    }

    return shows;

}

scrapeShow = async (showDiv: puppeteer.ElementHandle<Element>, dateString: string): Promise<Show> => {
  const timeString =  await showDiv.$eval(this.htmlConfig().selectedTimeSelector, getTextContent)
  const ticketLinkDivs = await showDiv.$$eval(this.htmlConfig().ticketLinkSelector, getPropertyOfElements, "href")
  const name =  await showDiv.$eval(this.htmlConfig().selectedOptionalShowNameSelector, getTextContent)
  const comedianDivList = await showDiv.$$(this.htmlConfig().setContentSelector);
  const comedians = await this.scrapeComediansFromLineupItem(comedianDivList);

  return {
     dateTime: combineDateAndTimeStrings(dateString, timeString ?? ""),
     name,
     comedians,
     ticketLink: combineWebsite(this.baseWebsite(), ticketLinkDivs),
  } as Show
}

scrapeComediansFromLineupItem = async (comedianDivList: puppeteer.ElementHandle<Element>[]): Promise<Comedian[]> => {
  const comedianList: Comedian[] = [];

  for (const comedianDiv of comedianDivList) {
     const comedian = await this.scrapeComedianDivForComedian(comedianDiv);
     comedianList.push(comedian);
  }

  return comedianList
}

scrapeComedianDivForComedian = async (element: puppeteer.ElementHandle<Element>): Promise<Comedian> => {
  const website = await element.$$eval(this.htmlConfig().comedianWebsiteSelector, getPropertyOfElements, "href")
  const name = await element.$eval(this.htmlConfig().comedianNameSelector, getTextContent)

  return {
      name,
      website: website[0],
  } as Comedian
}

}
