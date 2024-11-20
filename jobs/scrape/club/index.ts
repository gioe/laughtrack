
'use server';
import playwright from "playwright";
import { ScrapingOutput } from "../../../objects/interface";
import { runTasks } from "../../../util/promiseUtil";
import { flattenArrayList } from "../../../util/primatives/arrayUtil";
import { ClubDTO, ClubInterface } from "../../../objects/class/club/club.interface";
import { clubScrapingFunction } from "../../../util/scrape";
import { Club } from "../../../objects/class/club/Club";
import { getDB } from "../../../database";
const { database } = getDB();

export async function scrapeClubs(clubs: ClubDTO[], headless: boolean): Promise<string> {

    const ids = clubs.map((club: ClubDTO) => club.id)
    const startDate = new Date();
    console.log(`Started scraping job for ${ids.length == 0 ? "all" : ids} at ${startDate}`);

    const tasks = clubs.map((clubDto: ClubDTO) => {
        const club = new Club(clubDto)
        return runScraper(club, headless)
    })

    return runTasks(tasks)
        .then((scrapingOutput: ScrapingOutput[][]) => flattenArrayList(scrapingOutput))
        .then((scrapingOutput: ScrapingOutput[]) => storeOutput(scrapingOutput))
        .then(() => {

            const diffInMilliseconds = Math.abs(new Date().getTime() - startDate.getTime());

            const minutes = Math.floor(diffInMilliseconds / 60000);
            const seconds = Math.floor((diffInMilliseconds % 60000) / 1000);

            const message = `Finished scraping ${ids.toString()} in ${minutes} minutes and ${seconds} seconds.`;
            console.log(message)
            return message
        });
};


const runScraper = async (
    club: ClubInterface,
    headless?: boolean,
): Promise<ScrapingOutput[]> => {
    return playwright.chromium
        .launch({ headless: headless ?? false })
        .then((browser) => clubScrapingFunction(club, browser));
};

const storeOutput = async (all: ScrapingOutput[]): Promise<void> => {
    for (let index = 0; index < all.length - 1; index++) {
        await database.scrape.storeScrapingOutput(all[index]);
    }
};
