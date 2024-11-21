
'use server';
import playwright from "playwright";
import { getDB } from "../../../database";
const { database } = getDB();
import { ScrapingOutput } from "../../../objects/interface";
import { Show } from "../../../objects/class/show/Show";
import { Club } from "../../../objects/class/club/Club";
import { showScrapingFunction } from "../../../util/scrape";

export async function scrapeShow(show: Show, club: Club, headless: boolean, pause: boolean): Promise<string> {
    const startDate = new Date();
    console.log(`Started scraping job for ${show.id} at ${startDate}`);

    return runScraper(club, show, headless, pause)
        .then((scrapingOutput: ScrapingOutput) => storeOutput(scrapingOutput))
        .then(() => {

            const diffInMilliseconds = Math.abs(new Date().getTime() - startDate.getTime());

            const minutes = Math.floor(diffInMilliseconds / 60000);
            const seconds = Math.floor((diffInMilliseconds % 60000) / 1000);
            const message = `Finished scraping ${show.id} in ${minutes} minutes and ${seconds} seconds.`;

            console.log(message)
            return message
        });
};


const runScraper = async (
    club: Club,
    show: Show,
    headless: boolean,
    pause: boolean
): Promise<ScrapingOutput> => {
    return playwright.chromium
        .launch({ headless: headless ?? false })
        .then((browser) => showScrapingFunction(club, show.ticket.link, browser, pause));
};

const storeOutput = async (output: ScrapingOutput): Promise<void> => {
    await database.scrape.storeScrapingOutput(output);

};
