import * as showController from '../show'
import * as comedianController from '../comedian'
import * as lineupController from '../lineup'
import * as clubController from '../club'
import playwright from "playwright";

import { ScrapingOutput, ClubScrapingData } from "../../interfaces";
import { toCreateLineupItemDTOArray } from '../../util/domainModels/lineupItem/mapper';
import { providedPromiseResponse, runTasks } from '../../util/promiseUtil';
import { flattenArrayList } from '../../util/primatives/arrayUtil';
import {
    ComedyCellar,
    NewYorkComedyClub,
    TheStand,
    TheGrislyPear,
    TheTinyCupboard,
    UnionHall,
    WilliamsburgComedyClub,
    Rodneys,
    EastvilleComedyClub,
    Caveat,
    WestSideComedyClub,
    ComedyVillage
} from '../../jobs/scrape/clubs';

export const scrapeClubs = async (id: number[], headless?: boolean) => {
    const startDate = new Date()
    console.log(`Started scraping job for ${id} at ${startDate}`);

    await clubController.getAllScrapingData(id)
        .then((clubs: ClubScrapingData[]) => {
            const jobs = clubs
                .map((club: ClubScrapingData) => runScraper(club, headless))
            return runTasks(jobs)
        }) 
        .then((scrapingOutput: ScrapingOutput[][]) => flattenArrayList(scrapingOutput))
        .then((scrapingOutput: ScrapingOutput[]) => storeOutput(scrapingOutput))
        .then(() => console.log(`Finished in ${(new Date().getTime() - startDate.getTime()) / 1000} seconds`))
}

const storeOutput = async (all: ScrapingOutput[]): Promise<void> => {
    for (let index = 0; index < all.length - 1; index++) {
        await storeOutputInstance(all[index])
    }
}

const runScraper = async (club: ClubScrapingData, headless?: boolean): Promise<ScrapingOutput[]> => {
    return playwright.chromium.launch({ headless: headless ? headless : false })
        .then(browser => createScrapingFunction(club, browser))
}

const createScrapingFunction = (club: ClubScrapingData, browser: playwright.Browser): Promise<ScrapingOutput[]> => {
    switch (club.name) {
        case 'Comedy Cellar New York': return new ComedyCellar(club, browser).scrape();
        case 'New York Comedy Club East Village': return new NewYorkComedyClub(club, browser).scrape();
        case 'New York Comedy Club Upper West Side': return new NewYorkComedyClub(club, browser).scrape();
        case 'New York Comedy Club Midtown': return new NewYorkComedyClub(club, browser).scrape();
        case 'The Stand': return new TheStand(club, browser).scrape();
        case 'The Grisly Pear': return new TheGrislyPear(club, browser).scrape();
        case 'The Tiny Cupboard': return new TheTinyCupboard(club, browser).scrape();
        case 'Union Hall': return new UnionHall(club, browser).scrape();
        case 'Williamsburg Comedy Club': return new WilliamsburgComedyClub(club, browser).scrape();
        case 'Rodney’s': return new Rodneys(club, browser).scrape();
        case 'Eastville Comedy Club Brooklyn': return new EastvilleComedyClub(club, browser).scrape();
        case 'Comedy Village': return new ComedyVillage(club, browser).scrape();
        case 'Caveat': return new Caveat(club, browser).scrape();
        case "West Side Comedy Club": return new WestSideComedyClub(club, browser).scrape()
        default: throw new Error("No club name found")
    }

}

const storeOutputInstance = async (instance: ScrapingOutput): Promise<null> => {

    const show = await showController.add(instance.show)

    if (instance.comedians.length > 0) {
        const uuids = await comedianController.addAll(instance.comedians)
        const ids = await comedianController.getByUUIDs(uuids)
        const lineupItems = toCreateLineupItemDTOArray(ids, show.id)
        return lineupController.addAll(lineupItems)
    }

    return providedPromiseResponse(null)

}
