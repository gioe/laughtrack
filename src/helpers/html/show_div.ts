import puppeteer from 'puppeteer';
import { ClubConfig, Comedian, Show } from "../../types/index.js";
import { combineDateAndTimeStrings, convertDatetimeToLocalTimezone } from '../time/time_helpers.js';
import { scrapeComedianDivForComedian } from './comedian_div.js';


export const scrapeSelectedDateString = async (page: puppeteer.Page, clubConfig: ClubConfig): Promise<string> => {
   return await page.$(clubConfig.htmlConfig.selectedDateSelector).then(element => {
      return element?.evaluate(element => element.textContent)
  }) ?? "";
}

export const scrapeOptionalShowName = async (parentDiv: puppeteer.ElementHandle<Element>, clubConfig: ClubConfig): Promise<string> => {
   return await parentDiv.$(clubConfig.htmlConfig.selectedOptionalShowNameSelector).then(element => {
      return element?.evaluate(element => element.textContent)
   }) ?? "";
}

export const scrapeShowDateTime = async (parentDiv: puppeteer.ElementHandle<Element>, clubConfig: ClubConfig, dateString: string): Promise<Date> => {
  
   const showTime = await parentDiv.$(clubConfig.htmlConfig.selectedTimeSelector).then(element => {
       return element?.evaluate(element => element.textContent)
   });
   
   if (showTime) {
      return combineDateAndTimeStrings(dateString, showTime, clubConfig);
   } else {
      return new Date();
   }
}

export const scrapeComediansFromLineupItem = async (parentDiv: puppeteer.ElementHandle<Element>, clubConfig: ClubConfig): Promise<Comedian[]> => {
   const comedianDivList = (await parentDiv.$$(clubConfig.htmlConfig.setContentSelector));
   const comedianList: Comedian[] = [];

   for (const comedianDiv of comedianDivList) {
      const comedian = await scrapeComedianDivForComedian(comedianDiv, clubConfig);
      comedianList.push(comedian);
   }

   return comedianList
}

export const scrapeShowFromLineupItem = async (lineupItem: puppeteer.ElementHandle<Element>, clubConfig: ClubConfig, dateString: string): Promise<Show> => {
   const dateTime = await scrapeShowDateTime(lineupItem, clubConfig, dateString);
   const name = await scrapeOptionalShowName(lineupItem, clubConfig);
   const comedians = await scrapeComediansFromLineupItem(lineupItem, clubConfig);
   console.log(`Scraped ${name} on ${dateTime} with ${comedians.length} comedians.`);
   return {
      club: {
         name: clubConfig.name,
         city: clubConfig.city,
         website: clubConfig.website,
      },
      dateTime: convertDatetimeToLocalTimezone(dateTime, clubConfig),
      name,
      comedians,
   }
}