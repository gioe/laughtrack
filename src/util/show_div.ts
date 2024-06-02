import puppeteer from 'puppeteer';
import { HTMLConfigurable } from "../types/configs.interface.js";
import { Comedian } from "../types/comedian.interface.js";

import { combineDateAndTimeStrings, convertDatetimeToLocalTimezone } from '../util/time_helpers.js';
import { scrapeComedianDivForComedian } from './comedian_div.js';
import { Show } from '../types/show.interface.js';


export const scrapeSelectedDateString = async (page: puppeteer.Page, config: HTMLConfigurable): Promise<string> => {
   return await page.$(config.selectedDateSelector).then(element => {
      return element?.evaluate(element => element.textContent)
  }) ?? "";
}

export const scrapeOptionalShowName = async (parentDiv: puppeteer.ElementHandle<Element>, config: HTMLConfigurable): Promise<string> => {
   return await parentDiv.$(config.selectedOptionalShowNameSelector).then(element => {
      return element?.evaluate(element => element.textContent)
   }) ?? "";
}

export const scrapeShowDateTime = async (parentDiv: puppeteer.ElementHandle<Element>, config: HTMLConfigurable, dateString: string): Promise<Date> => {
  
   const showTime = await parentDiv.$(config.selectedTimeSelector).then(element => {
       return element?.evaluate(element => element.textContent)
   });
   
   if (showTime) {
      return combineDateAndTimeStrings(dateString, showTime, config);
   } else {
      return new Date();
   }
}

export const scrapeComediansFromLineupItem = async (parentDiv: puppeteer.ElementHandle<Element>, config: HTMLConfigurable): Promise<Comedian[]> => {
   const comedianDivList = (await parentDiv.$$(config.setContentSelector));
   const comedianList: Comedian[] = [];

   for (const comedianDiv of comedianDivList) {
      const comedian = await scrapeComedianDivForComedian(comedianDiv, config);
      comedianList.push(comedian);
   }

   return comedianList
}

export const scrapeShowFromLineupItem = async (lineupItem: puppeteer.ElementHandle<Element>, config: HTMLConfigurable, dateString: string): Promise<Show> => {
   const dateTime = await scrapeShowDateTime(lineupItem, config, dateString);
   const name = await scrapeOptionalShowName(lineupItem, config);
   const comedians = await scrapeComediansFromLineupItem(lineupItem, config);
   return {
      club: {
         name: config.name,
         website: config.website,
      },
      dateTime: convertDatetimeToLocalTimezone(dateTime, ""),
      name,
      comedians,
   } as Show
}