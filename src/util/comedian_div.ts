import puppeteer from 'puppeteer';
import { ClubConfig, Comedian } from "../types/index.js";

export const scrapeComedianDivForComedian = async (element: puppeteer.ElementHandle<Element>, clubConfig: ClubConfig): Promise<Comedian> => {
    const name = await getComedianNameFromElement(element, clubConfig);
    const website = (await getComedianWebsiteFromElement(element, clubConfig)).toLowerCase();

    return {
        name,
        website,
    };
}

const getComedianNameFromElement = async (element: puppeteer.ElementHandle<Element>, clubConfig: ClubConfig): Promise<string> => {
    return await element.$(clubConfig.htmlConfig.comedianNameSelector).then(element => {
        return element?.evaluate(element => element.textContent)
    }) ?? "";
}

const getComedianWebsiteFromElement = async (element: puppeteer.ElementHandle<Element>, clubConfig: ClubConfig): Promise<string> => {
    const websites =  await element.$$eval(clubConfig.htmlConfig.comedianWebsiteSelector, elements => elements.map(element => element.getAttribute('href')));
    return websites[0] ?? "";
}

