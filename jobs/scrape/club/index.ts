
'use server';
import playwright from "playwright";
import { getDB } from "../../../database";
import { LineupItemDTO, ScrapingOutput } from "../../../objects/interfaces";

import { providedPromiseResponse, runTasks } from "../../../util/promiseUtil";
import { flattenArrayList } from "../../../util/primatives/arrayUtil";
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
    ComedyVillage,
} from "../clubs";
import { ClubInterface } from "../../../objects/classes/club/club.interface";
import { ComedyClub } from "../../../util/enum";
import { ComedianDTO } from "../../../objects/classes/comedian/comedian.interface";
const { db } = getDB()

export async function scrapeClubs(clubIds?: string[], headless?: boolean): Promise<string> {

    const ids = clubIds ?? [];
    const idNumbers = ids.map((id: string) => Number(id));
    const startDate = new Date();
    console.log(`Started scraping job for ${idNumbers.length == 0 ? "all" : ids} at ${startDate}`);

    return db.clubs.getAllForScraping()
        .then((clubs: ClubInterface[]) => {
            const jobs = clubs.filter((club: ClubInterface) => {
                if (ids.length > 0) return idNumbers.includes(club.id)
                return true
            }).map((club: ClubInterface) =>
                runScraper(club, headless),
            );
            return runTasks(jobs);
        })
        .then((scrapingOutput: ScrapingOutput[][]) => flattenArrayList(scrapingOutput))
        .then((scrapingOutput: ScrapingOutput[]) => storeOutput(scrapingOutput))
        .then(() => {

            const diffInMilliseconds = Math.abs(new Date().getTime() - startDate.getTime());

            const minutes = Math.floor(diffInMilliseconds / 60000);
            const seconds = Math.floor((diffInMilliseconds % 60000) / 1000);

            const message = `Finished scraping ${idNumbers.toString()} in ${minutes} minutes and ${seconds} seconds.`;
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
        .then((browser) => createScrapingFunction(club, browser));
};

const createScrapingFunction = (
    club: ClubInterface,
    browser: playwright.Browser,
): Promise<ScrapingOutput[]> => {
    switch (club.name) {
        case ComedyClub.ComedyCellarNewYork:
            return new ComedyCellar(club, browser).scrape();
        case ComedyClub.NewYorkComedyClubUpperWestSide:
            return new NewYorkComedyClub(club, browser).scrape();
        case ComedyClub.NewYorkComedyClubMidtown:
            return new NewYorkComedyClub(club, browser).scrape();
        case ComedyClub.NewYorkComedyClubEastVillage:
            return new NewYorkComedyClub(club, browser).scrape();
        case ComedyClub.TheStand:
            return new TheStand(club, browser).scrape();
        case ComedyClub.TheGrislyPear:
            return new TheGrislyPear(club, browser).scrape();
        case ComedyClub.TheTinyCupboard:
            return new TheTinyCupboard(club, browser).scrape();
        case ComedyClub.UnionHall:
            return new UnionHall(club, browser).scrape();
        case ComedyClub.WilliamsburgComedyClub:
            return new WilliamsburgComedyClub(club, browser).scrape();
        case ComedyClub.Rodneys:
            return new Rodneys(club, browser).scrape();
        case ComedyClub.EastvilleComedyClubBrooklyn:
            return new EastvilleComedyClub(club, browser).scrape();
        case ComedyClub.ComedyVillage:
            return new ComedyVillage(club, browser).scrape();
        case ComedyClub.Caveat:
            return new Caveat(club, browser).scrape();
        case ComedyClub.WestSideComedyClub:
            return new WestSideComedyClub(club, browser).scrape();
        default:
            throw new Error("No club name found");
    }
};

const storeOutputInstance = async (instance: ScrapingOutput): Promise<null> => {
    const show = await db.shows.add(instance.show);

    if (instance.comedians.length > 0) {
        return db.comedians.addAll(instance.comedians)
            .then(() => {
                const uuids = instance.comedians.map((comedian: ComedianDTO) => comedian.uuid)
                return db.comedians.getIds(uuids);
            })
            .then((comedianIds: { id: number }[]) => {
                const lineupItems = comedianIds.map((comedianId: { id: number }) => {
                    return {
                        show_id: show.id,
                        comedian_id: comedianId.id
                    }
                }) as LineupItemDTO[]
                return db.lineupItems.addAll(lineupItems);
            })
    }

    return providedPromiseResponse(null);
};

