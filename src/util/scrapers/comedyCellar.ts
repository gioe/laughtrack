import puppeteer from 'puppeteer';
import { HTMLConfigurable } from "../../types/configs.interface.js";
import { getOptionsProperty, getTextContent } from '../html/element.js';
import { writeToFirestore } from '../../util/storage/dataStore.js';
import { addDelay, cleanDateString, cleanTimeString, combineDateAndTimeStrings, convertDatetimeToString } from '../dateTime.js';
import { Show } from '../../types/show.interface.js';
import { Scraper } from '../../types/scraper.interface.js';
import { Comedian } from '../../types/comedian.interface.js';


export class ComedyCellarScaper implements Scraper {
  config: HTMLConfigurable;

  public constructor(config: HTMLConfigurable) {
    this.config = config;
  }

  scrape = async (page: puppeteer.Page) => {
    await page.goto(this.config.website)

    // Get the date do
    const allDates = await page.$$eval(this.config.allDateOptionsSelector, getOptionsProperty, "value")

    const scrapedShows: Show[] = [];

    for (let i = 0; i < allDates.length - 1; i++) {   
      const shows = await this.scrapeShowsOnDate(allDates[i], page);    

      scrapedShows.push(...shows);

      await page.select(this.config.dateMenuSelector, allDates[i+1]);

      await addDelay(100);
    }

    writeToFirestore(scrapedShows, this.config);
    
  }
  

private scrapeShowsOnDate = async (dateString: string, page: puppeteer.Page,) => {
    const showDivs = await page.$$(this.config.allShowsSelector);

    const shows: Show[] = [];

    for (const showDiv of showDivs) {
      const show = await this.scrapeShow(showDiv, dateString);
      shows.push(show);
    }

    return shows;

}

scrapeShow = async (showDiv: puppeteer.ElementHandle<Element>, dateString: string): Promise<Show> => {
  const timeString =  await showDiv.$eval(this.config.selectedTimeSelector, getTextContent)
  const name =  await showDiv.$eval(this.config.selectedOptionalShowNameSelector, getTextContent)
  
  const comedians = await this.scrapeComediansFromLineupItem(showDiv);

  return {
     dateTime: this.transformDateTime(dateString, timeString ?? ""),
     name,
     comedians,
  } as Show
}

transformDateTime = (dateString: string, timeString: string): string => {
  const cleanedDateString = cleanDateString(dateString, this.config.extraDateString);
  const cleanedTimeString = cleanTimeString(timeString, this.config.extraTimeString);
  const date = combineDateAndTimeStrings(dateString, timeString) ?? new Date()
  return convertDatetimeToString(date);
}


scrapeComediansFromLineupItem = async (parentDiv: puppeteer.ElementHandle<Element>): Promise<Comedian[]> => {
  const comedianDivList = (await parentDiv.$$(this.config.setContentSelector));
  const comedianList: Comedian[] = [];

  for (const comedianDiv of comedianDivList) {
     const comedian = await this.scrapeComedianDivForComedian(comedianDiv);
     comedianList.push(comedian);
  }

  return comedianList
}

scrapeComedianDivForComedian = async (element: puppeteer.ElementHandle<Element>): Promise<Comedian> => {
  const website = await element.$$eval(this.config.comedianWebsiteSelector, getOptionsProperty, "href")
  const name = await element.$eval(this.config.comedianNameSelector, getTextContent)

  return {
      name,
      website: website[0],
  } as Comedian
}

}
