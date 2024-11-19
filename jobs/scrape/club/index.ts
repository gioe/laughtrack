
'use server';
import playwright from "playwright";
import { LineupItemDTO, ScrapingOutput } from "../../../objects/interface";
import { providedPromiseResponse, runTasks } from "../../../util/promiseUtil";
import { flattenArrayList } from "../../../util/primatives/arrayUtil";
import { ClubDTO, ClubInterface } from "../../../objects/class/club/club.interface";
import { clubScrapingFunction } from "../../../util/scrape";
import { Club } from "../../../objects/class/club/Club";
import { getDB } from "../../../database";
import { ComedianDTO } from "../../../objects/class/comedian/comedian.interface";
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


const storeOutput = async (all: ScrapingOutput[]): Promise<void> => {
    for (let index = 0; index < all.length - 1; index++) {
        await storeOutputInstance(all[index]);
    }
};

const runScraper = async (
    club: ClubInterface,
    headless?: boolean,
): Promise<ScrapingOutput[]> => {
    return playwright.chromium
        .launch({ headless: headless ?? false })
        .then((browser) => clubScrapingFunction(club, browser));
};


const storeOutputInstance = async (output: ScrapingOutput): Promise<null> => {
    const show = await database.scrapingUtil.addShow(output.show);

    if (output.comedians.length > 0) {
        return database.scrapingUtil.addComedians(output.comedians)
            .then(() => {
                const uuids = output.comedians.map((comedian: ComedianDTO) => comedian.uuid).filter((value: string | undefined) => value !== undefined)
                return database.scrapingUtil.getComedianIds(uuids);
            })
            .then((comedianIds: { id: number }[]) => {
                const lineupItems = comedianIds.map((comedianId: { id: number }) => {
                    return {
                        show_id: show.id,
                        comedian_id: comedianId.id
                    }
                }) as LineupItemDTO[]
                return database.scrapingUtil.addLineupItems(lineupItems);
            })
    }


    return providedPromiseResponse(null);
};

