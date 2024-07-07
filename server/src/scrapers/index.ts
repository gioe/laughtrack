import { readJsonFile } from "../util/storage/fileSystem.js";
import { writeToFirestore } from '../util/storage/fireStore.js';
import { FIRESTORE_COLLECTIONS } from '../constants/firestore.js';
import { Comedian } from "../classes/Comedian.js";
import { Scraper } from "../classes/Scraper.js";
import puppeteer from "puppeteer";
import { cleanComedianList, flattenComedians } from "../util/types/comedianUtil.js";
import { ScraperInterface } from "../types/scraper.interface.js";

const scrapers = readJsonFile(process.env.SCRAPERS_FILE ?? "src/scrapers.json") as ScraperInterface[];

export const scrapeAllClubs = async () => {
    console.log(`Started all scraping jobs at ${new Date()}`);

    puppeteer.launch({ dumpio: true })
    .then(browser => {
        return parallelizeScrapers(browser)
    })
    .then((comedians: Comedian[]) => {
        const cleanedComedians = cleanComedianList(comedians);
        // storeData(comedians)
    })
}

const parallelizeScrapers = async (browser: puppeteer.Browser): Promise<Comedian[]> => {
    return Promise.all(getIndividualTasks(browser))
    .then((comedianArrays: Comedian[][]) =>  flattenComedians(comedianArrays));
}

const getIndividualTasks = (browser: puppeteer.Browser): Promise<Comedian[]>[]  => {
    return scrapers.map((scraperModel: ScraperInterface) => { 
        const scraper = new Scraper(scraperModel, browser)
        return scraper.scrape();
    })
};

const storeData = (scrapedComedians: Comedian[]) => {
    scrapedComedians.forEach(comedian => {
        writeToFirestore(FIRESTORE_COLLECTIONS.comedians, comedian)
    })
}