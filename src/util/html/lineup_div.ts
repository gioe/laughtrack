import puppeteer from "puppeteer";
import { HTMLConfigurable } from "../../types/configs.interface.js";
import { scrapeShowFromLineupItem } from './show_div.js';
import { Show } from "../../types/show.interface.js";

export const getLineupsParent = async (page: puppeteer.Page, config: HTMLConfigurable) => {
    return await page.$(config.lineupsParentSelector);
}

export const scrapeLineups = async (page: puppeteer.Page, config: HTMLConfigurable, dateString: string) => {
    // While looping through each date in the dropdown, the page will be updated with the new lineup.
    // This will be called for every unique page instance.
    const lineupItems = await getLineupItems(page, config);
    const shows: Show[] = [];

    if (lineupItems) {
        for (const lineupItem of lineupItems) {
            const show = await scrapeShowFromLineupItem(lineupItem, config, dateString);
            shows.push(show);
        }
    }
    
    return shows;
}


export const getLineupItems = async (page: puppeteer.Page,  config: HTMLConfigurable) => {
    const lineupsParent = await getLineupsParent(page, config);
    if (lineupsParent) {
        return await lineupsParent.$$(config.lineupItemsSelector);
    } 

}