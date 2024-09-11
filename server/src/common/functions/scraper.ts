import chromium from "@sparticuz/chromium";
import playwright, { Browser } from "playwright-core";
import { ClubInterface } from "../interfaces/club.interface.js";
import { ShowInterface } from "../interfaces/show.interface.js";
import { Scraper } from "../../jobs/classes/models/Scraper.js";

export const runScraper = async (club: ClubInterface): Promise<ShowInterface[]> => {
    return chromium.executablePath()
    .then((executablePath: any) => {
        return playwright.chromium.launch({
            executablePath,
            headless: true, 
            args: chromium.args
          })
        })
        .then(browser => getScrapingJob(browser, club))
}

const getScrapingJob = (browser: playwright.Browser, club: ClubInterface): Promise<ShowInterface[]> => {
    return new Scraper(club, browser).scrape()
};
