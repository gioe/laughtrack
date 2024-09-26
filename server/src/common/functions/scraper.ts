import playwright from "playwright";
import StealthPlugin from 'puppeteer-extra-plugin-stealth'
import { ClubInterface } from "../interfaces/club.interface.js";
import { ShowInterface } from "../interfaces/show.interface.js";
import { Scraper } from "../../jobs/classes/models/Scraper.js";
import { processShows } from "../../database/util/showUtil.js";
import { chromium } from 'playwright-extra'
import { Show } from "../../jobs/classes/models/Show.js";

export const runScraper = async (club: ClubInterface): Promise<ShowInterface[]> => {
    chromium.use(StealthPlugin())
    return playwright.chromium.launch({ headless: true })
        .then(browser => getScrapingJob(browser, club))
}

const getScrapingJob = (browser: playwright.Browser, club: ClubInterface): Promise<ShowInterface[]> => {
    return new Scraper(club, browser).scrape().then(((shows: ShowInterface[]) => processShows(club, shows as Show[])));
};
