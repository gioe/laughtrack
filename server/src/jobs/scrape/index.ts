
import * as clubController from "../../api/controllers/club/index.js"
import * as scrapingController from  "../../api/controllers/scrape/index.js"

import playwright from "playwright";
import { ClubScrapingData } from "../../common/models/interfaces/club.interface.js";
import { ScrapingOutput } from "../../common/models/interfaces/scrape.interface.js";
import { writeLogToFile } from "../../common/util/logUtil.js";
import { flattenArrayList } from "../../common/util/primatives/arrayUtil.js";
import { runTasks } from "../../common/util/promiseUtil.js";
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
} from "./clubs/index.js"

async function runScrapingJob() {
    const args = process.argv.slice(2);
    const idArg = args.find((arg) => arg.startsWith("--arg="));
    const idString = idArg ? idArg.split("=")[1] : "";
    const ids = idString ? idString.split(",") : []
    const idNumbers = ids.map((id: string) => Number(id))
    writeLogToFile("Running scraping job")
    scrapeClubs(idNumbers)
}

export const scrapeClubs = async (id: number[]) => {
    const startDate = new Date()
    writeLogToFile(`Started all scraping jobs at ${startDate}`);

    await clubController.getAllScrapingData()
        .then((clubs: ClubScrapingData[]) => {
            const jobs = clubs
            .filter((club: ClubScrapingData) =>  id.length > 0 ? id.includes(club.id) : true)
            .map((club: ClubScrapingData) => runScraper(club))
            return runTasks(jobs)
        })
        .then((scrapingOutput: ScrapingOutput[][]) => flattenArrayList(scrapingOutput))
        .then((scrapingOutput: ScrapingOutput[]) => scrapingController.storeOutput(scrapingOutput))

    writeLogToFile(`Finished in ${(new Date().getTime() - startDate.getTime()) / 1000} seconds`);
}


export const runScraper = async (club: ClubScrapingData): Promise<ScrapingOutput[]> => {
    return playwright.chromium.launch({ headless: false })
        .then(browser => createScrapingFunction(club, browser))
}

export const createScrapingFunction = (club: ClubScrapingData, browser: playwright.Browser): Promise<ScrapingOutput[]> => {
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

runScrapingJob();
