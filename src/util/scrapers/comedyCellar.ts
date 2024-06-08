import puppeteer from 'puppeteer';
import { HTMLConfigurable } from "../../types/configs.interface.js";
import { getOptionsProperty, getTextContent } from '../html/element.js';
import { writeToFirestore } from '../../util/storage/dataStore.js';
import { addDelay, cleanDateString, cleanTimeString, combineDateAndTimeStrings, convertDatetimeToString } from '../dateTime.js';
import { Show } from '../../types/show.interface.js';
import { Scraper } from '../../types/scraper.interface.js';
import { Comedian } from '../../types/comedian.interface.js';
import { Club } from '../../types/club.interface.js';
import { Writable } from '../../types/writable.interface.js';

export class ComedyCellarScaper implements Scraper {
  private club: Club;

  public constructor(club: Club) {
    this.club = club
  }

  private htmlConfig() {
    return (this.club as HTMLConfigurable).htmlConfig;
  }

  private storagePath() {
    return (this.club as Writable).storagePath;
  }

  private website() {
    return this.club.website
  }

  scrape = async (page: puppeteer.Page) => {
    console.log(`Scraping ${this.website()}`)
    await page.goto(this.website())

    // Get the date do
    const allDates = await page.$$eval(this.htmlConfig().allDateOptionsSelector, getOptionsProperty, "value")

    const scrapedShows: Show[] = [];

    for (let i = 0; i < allDates.length - 1; i++) {   
      const shows = await this.scrapeShowsOnDate(allDates[i], page);    
      scrapedShows.push(...shows);

      await page.select(this.htmlConfig().dateMenuSelector, allDates[i+1]);

      await addDelay(100);
    }

    if (scrapedShows.length == 0) {
      console.log(`Scraper returned no shows for ${this.website}`)
    } else {
      writeToFirestore(scrapedShows, this.storagePath());
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
  const name =  await showDiv.$eval(this.htmlConfig().selectedOptionalShowNameSelector, getTextContent)
  
  const comedians = await this.scrapeComediansFromLineupItem(showDiv);

  return {
     dateTime: this.transformDateTime(dateString, timeString ?? ""),
     name,
     comedians,
  } as Show
}

transformDateTime = (dateString: string, timeString: string): string => {
  const cleanedDateString = cleanDateString(dateString, this.htmlConfig().extraDateString);
  const cleanedTimeString = cleanTimeString(timeString, this.htmlConfig().extraTimeString);
  const date = combineDateAndTimeStrings(dateString, timeString) ?? new Date()
  return convertDatetimeToString(date);
}


scrapeComediansFromLineupItem = async (parentDiv: puppeteer.ElementHandle<Element>): Promise<Comedian[]> => {
  const comedianDivList = (await parentDiv.$$(this.htmlConfig().setContentSelector));
  const comedianList: Comedian[] = [];

  for (const comedianDiv of comedianDivList) {
     const comedian = await this.scrapeComedianDivForComedian(comedianDiv);
     comedianList.push(comedian);
  }

  return comedianList
}

scrapeComedianDivForComedian = async (element: puppeteer.ElementHandle<Element>): Promise<Comedian> => {
  const website = await element.$$eval(this.htmlConfig().comedianWebsiteSelector, getOptionsProperty, "href")
  const name = await element.$eval(this.htmlConfig().comedianNameSelector, getTextContent)

  return {
      name,
      website: website[0],
  } as Comedian
}

}
