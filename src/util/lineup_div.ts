import puppeteer from "puppeteer";
import { ClubConfig, Show } from "../types/configs.interface.js";
import { scrapeShowFromLineupItem } from './show_div.js';

export const getLineupsParent = async (page: puppeteer.Page, clubConfig: ClubConfig) => {
    return await page.$(clubConfig.htmlConfig.lineupsParentSelector);
}

export const scrapeLineups = async (page: puppeteer.Page, clubConfig: ClubConfig, dateString: string) => {
    // While looping through each date in the dropdown, the page will be updated with the new lineup.
    // This will be called for every unique page instance.
    const lineupItems = await getLineupItems(page, clubConfig);
    const shows: Show[] = [];

    if (lineupItems) {
        for (const lineupItem of lineupItems) {
            const show = await scrapeShowFromLineupItem(lineupItem, clubConfig, dateString);
            shows.push(show);
        }
    }
    
    return shows;
}


export const getLineupItems = async (page: puppeteer.Page,  clubConfig: ClubConfig) => {
    const lineupsParent = await getLineupsParent(page, clubConfig);
    if (lineupsParent) {
        return await lineupsParent.$$(clubConfig.htmlConfig.lineupItemsSelector);
    } 

}