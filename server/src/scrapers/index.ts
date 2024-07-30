import { readJsonFile } from "../util/storage/fileSystem.js";
import { writeToFirestore } from '../util/storage/fireStore.js';
import { FIRESTORE_COLLECTIONS } from '../constants/firestore.js';
import { Comedian } from "../classes/Comedian.js";
import puppeteer from "puppeteer";
import { flattenElements } from "../util/types/arrayUtil.js";
import { cleanFinalComedianList } from "../util/types/comedianUtil.js";
import { Club } from "../classes/Club.js";
import { DateTimeScraper } from "./DateTimeScraper.js";
import { ShowScraper } from "./ShowScraper.js";
import { ComedianScraper } from "./ComedianScraper.js";
import { ClubScraper } from "./ClubScraper.js";


const scrapers = readJsonFile(process.env.SCRAPERS_FILE ?? "src/scrapers.json")

export const scrapeAllClubs = async () => {
    const startDate = new Date()
    console.log(`Started all scraping jobs at ${startDate}`);

    puppeteer.launch({ dumpio: true, pipe: true })
        .then(browser => runScrapers(browser))
        .then((comedians: Comedian[]) => {
            const cleanedComedians = cleanFinalComedianList(comedians);
            storeData(cleanedComedians)
            logCompletionTime(startDate)
        })
}

const logCompletionTime = (startDate: Date) => {
    console.log(`Finished in ${(new Date().getTime() - startDate.getTime()) / 1000} seconds`);
}

const runScrapers = async (browser: puppeteer.Browser): Promise<Comedian[]> => {
    return Promise.all(getIndividualTasks(browser))
        .then((comedianArrays: Comedian[][]) => flattenElements(comedianArrays));
}


const getIndividualTasks = (browser: puppeteer.Browser): Promise<Comedian[]>[] => {
    
    const ALL_CLUBS = [
        "Comedy Cellar New York", 
        "Comedy Cellar Las Vegas", 
        "Comic Strip Live NYC",
        "New York Comedy Club Midtown",
        "New York Comedy Club East Village",
        "New York Comedy Club Upper West Side",
        "The Stand"
     ]

    return scrapers
    .map((json: any) => {
        const club = new Club(json)
        const dateTimeScraper = new DateTimeScraper(club);

        const comedianScraper = new ComedianScraper(json);

        const showScraper = new ShowScraper(club, comedianScraper, dateTimeScraper);

        const clubScraper = new ClubScraper(club, browser, showScraper)

        return clubScraper.scrape()
    });
};

const storeData = (scrapedComedians: Comedian[]) => {
    scrapedComedians.forEach(comedian => {
        console.log(`Writing ${comedian.name} to storage`)
        return writeToFirestore(FIRESTORE_COLLECTIONS.comedians, comedian)}
    )
}