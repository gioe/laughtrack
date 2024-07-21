import { readJsonFile } from "../util/storage/fileSystem.js";
import { writeToFirestore } from '../util/storage/fireStore.js';
import { FIRESTORE_COLLECTIONS } from '../constants/firestore.js';
import { Comedian } from "../classes/Comedian.js";
import { ClubScraper } from "../classes/ClubScraper.js";
import puppeteer from "puppeteer";
import { flattenElements } from "../util/types/arrayUtil.js";
import { cleanFinalComedianList } from "../util/types/comedianUtil.js";
import { Club } from "../classes/Club.js";
import { SCRAPER_KEYS } from "../constants/objects.js";
import { ComedianScraper } from "../classes/ComedianScraper.js";
import { ElementScaper } from "../classes/ElementScaper.js";
import { Logger } from "../classes/Logger.js";
import { ShowScraper } from "../classes/ShowScraper.js";
import { DateTimeScraper } from "../classes/DateTimeScraper.js";

const scrapers = readJsonFile(process.env.SCRAPERS_FILE ?? "src/scrapers.json")

export const scrapeAllClubs = async () => {
    console.log(`Started all scraping jobs at ${new Date()}`);

    puppeteer.launch({ dumpio: true, pipe: true })
        .then(browser => runScrapers(browser))
        .then((comedians: Comedian[]) => {
            const cleanedComedians = cleanFinalComedianList(comedians);
            storeData(cleanedComedians)
        })
}

const runScrapers = async (browser: puppeteer.Browser): Promise<Comedian[]> => {
    return Promise.all(getIndividualTasks(browser))
        .then((comedianArrays: Comedian[][]) => flattenElements(comedianArrays));
}

const getIndividualTasks = (browser: puppeteer.Browser): Promise<Comedian[]>[] => {
    return scrapers.map((json: any) => {

        const club = new Club(json[SCRAPER_KEYS.club])
        const logger = new Logger("https://www.comedycellar.com/new-york-line-up/");

        const elementScraper = new ElementScaper(club, logger);
        const dateTimeScraper = new DateTimeScraper(club, json, elementScraper, logger);
        const showScraper = new ShowScraper(club, json, elementScraper, dateTimeScraper, logger);
        const comedianScraper = new ComedianScraper(club, json, elementScraper, showScraper, logger);
        const clubScraper = new ClubScraper(club, json, browser, elementScraper, comedianScraper, logger)

        return clubScraper.scrape()
    });
};

const storeData = (scrapedComedians: Comedian[]) => {
    scrapedComedians.forEach(comedian => writeToFirestore(FIRESTORE_COLLECTIONS.comedians, comedian))
}