import puppeteer from 'puppeteer';
import { ClubConfig, Show } from '../types/index.js';
import { getDateDropdown, getDateDropdownItems, getSelectedValue } from '../helpers/html/datedropdown_div.js';
import { scrapeLineups } from '../helpers/html/lineup_div.js';
import { writeToDatabase } from '../helpers/storage/data_store.js';

export const scrapeComedyCellar = async (config: ClubConfig) => {

    const browser = await puppeteer.launch({ dumpio: true });
    const page = await browser.newPage();

    await page.goto(config.website)

    // Pages with date dropdowns require different handling than those without. 
    // First check for the existence of a date dropdown.
    const dateDropdown = await getDateDropdown(page, config)

    if (dateDropdown) {
      await loopThroughDates(page, dateDropdown, config);
    } else {
      // TODO: Get the default date if for some reason there's no datedropdown picked up
    }

    await browser.close();
}

const loopThroughDates = async (page: puppeteer.Page, dateDropdown: puppeteer.ElementHandle<Element>, config: ClubConfig): Promise<Show[]> => {
    // If the page has a date dropdown, it means there are many different dates to scrape. We'll need access to them all
    // to get the lionups for each date.
    const allDateDropdownItems = await getDateDropdownItems(page, config);
    const shows: Show[] = [];

    for (let i = 0; i < allDateDropdownItems.length - 1; i++) {   
      const currentSelectedDate = await getSelectedValue(page);   
      const selectedDateShows = await scrapeLineups(page, config, currentSelectedDate);    
      shows.push(...selectedDateShows);
      await page.select("select#cc_lineup_select_dates", allDateDropdownItems[i+1]);
      await delay(100);
    }

    writeToDatabase(shows);
    return shows;
}

function delay(time: number) {
  return new Promise(function(resolve) { 
      setTimeout(resolve, time)
  });
}