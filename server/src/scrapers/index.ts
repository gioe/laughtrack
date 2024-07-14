import { readJsonFile } from "../util/storage/fileSystem.js";
import { writeToFirestore } from '../util/storage/fireStore.js';
import { FIRESTORE_COLLECTIONS } from '../constants/firestore.js';
import { Comedian } from "../classes/Comedian.js";
import { ScrapingManager } from "../classes/ClubScraper.js";
import puppeteer from "puppeteer";
import { ScraperInterface } from "../types/scraper.interface.js";
import { flattenElements } from "../util/types/arrayUtil.js";
import { Logger } from "../classes/Logger.js";
import { cleanFinalComedianList } from "../util/types/comedianUtil.js";

const scrapers = readJsonFile(process.env.SCRAPERS_FILE ?? "src/scrapers.json") as ScraperInterface[];
const logger = new Logger("https://www.comedycellar.com/new-york-line-up/");

export const scrapeAllClubs = async () => {
    console.log(`Started all scraping jobs at ${new Date()}`);

    puppeteer.launch({ dumpio: true, pipe: true })
    .then(browser => {
        return parallelizeScrapers(browser)
    })
    .then((comedians: Comedian[]) => {
        const cleanedComedians = cleanFinalComedianList(comedians);
        // storeData(comedians)
    })
}

const parallelizeScrapers = async (browser: puppeteer.Browser): Promise<Comedian[]> => {
    return Promise.all(getIndividualTasks(browser))
    .then((comedianArrays: Comedian[][]) =>  flattenElements(comedianArrays));
}

const getIndividualTasks = (browser: puppeteer.Browser): Promise<Comedian[]>[]  => {
    return scrapers.map((scraperModel: ScraperInterface) => { 
        return new ScrapingManager(scraperModel, browser, logger).scrape()
    })
};

const storeData = (scrapedComedians: Comedian[]) => {
    scrapedComedians.forEach(comedian => {
        writeToFirestore(FIRESTORE_COLLECTIONS.comedians, comedian)
    })
}

const log = (input: any) => {
    logger.log(logger.baseSite, input)
  }