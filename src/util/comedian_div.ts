import puppeteer from 'puppeteer';
import { HTMLConfigurable } from "../types/configs.interface.js";
import { Comedian } from '../types/comedian.interface.js';

export const scrapeComedianDivForComedian = async (element: puppeteer.ElementHandle<Element>, config: HTMLConfigurable): Promise<Comedian> => {
    const name = await getComedianNameFromElement(element, config);
    const website = (await getComedianWebsiteFromElement(element, config)).toLowerCase();

    return {
        name,
        website,
    } as Comedian
}

const getComedianNameFromElement = async (element: puppeteer.ElementHandle<Element>, config: HTMLConfigurable): Promise<string> => {
    return await element.$(config.comedianNameSelector).then(element => {
        return element?.evaluate(element => element.textContent)
    }) ?? "";
}

const getComedianWebsiteFromElement = async (element: puppeteer.ElementHandle<Element>, config: HTMLConfigurable): Promise<string> => {
    const websites =  await element.$$eval(config.comedianWebsiteSelector, elements => elements.map(element => element.getAttribute('href')));
    return websites[0] ?? "";
}

