import playwright from "playwright";
import { readJsonFile } from "../util/storage/fileSystem.js";
import { writeToFirestore } from '../util/storage/fireStore.js';
import { FIRESTORE_COLLECTIONS } from '../constants/firestore.js';
import { Comedian } from "../classes/Comedian.js";
import { flattenElements } from "../util/types/arrayUtil.js";
import { cleanFinalComedianList } from "../util/types/comedianUtil.js";
import { Club } from "../classes/Club.js";
import { PageManager } from "./PageManager.js";
import { ScrapingConfig } from "../classes/ScrapingConfig.js";
import { Scraper } from "./Scraper.js";
import { InteractionConfig } from "../classes/InteractionConfig.js";
import { CLUB_KEYS, JSON_KEYS } from "../constants/objects.js";

const clubs = readJsonFile(process.env.CLUBS_FILE ?? "src/clubs.json")

export const scrapeAllClubs = async () => {
    const startDate = new Date()
    console.log(`Started all scraping jobs at ${startDate}`);

    playwright.chromium.launch({ headless: false })
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

const runScrapers = async (browser: playwright.Browser): Promise<Comedian[]> => {
    return Promise.all(getIndividualTasks(browser))
        .then((comedianArrays: Comedian[][]) =>  flattenElements(comedianArrays));
}


const getIndividualTasks = (browser: playwright.Browser): Promise<Comedian[]>[] => {

    const ALL_CLUBS = [
        "Comedy Cellar New York",
        "New York Comedy Club Midtown",
        "New York Comedy Club East Village",
        "New York Comedy Club Upper West Side",
        "The Stand",
        "The Grisly Pear",
        "The Tiny Cupboard",
        "West Side Comedy Club",
        "The Bell House",
        "Union Hall"
    ]

    return clubs
        .flatMap((json: any) => {
            const clubNames = json[JSON_KEYS.clubs]

            const interactionConfig = new InteractionConfig(json[JSON_KEYS.interactionConfig]);
            const scrapingConfig = new ScrapingConfig(json[JSON_KEYS.scrapingConfig]);

            const pageManager = new PageManager(interactionConfig, scrapingConfig);

            return clubNames
            .map((clubJson: any) => {
                const club = new Club(clubJson)
                return new Scraper(club, browser, pageManager, interactionConfig).scrape()
            })

        })
};

const storeData = (scrapedComedians: Comedian[]) => {
    scrapedComedians.forEach(comedian => {
        console.log(`Writing ${comedian.name} to storage`)
        // writeToFirestore(FIRESTORE_COLLECTIONS.comedians, comedian)
    })
}