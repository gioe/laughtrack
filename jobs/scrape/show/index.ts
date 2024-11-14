
'use server';
import playwright from "playwright";
import { getDB } from "../../../database";
import { LineupItemDTO, ScrapingOutput } from "../../../objects/interface";

import { providedPromiseResponse } from "../../../util/promiseUtil";
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
import { ComedyClub } from "../../../objects/enum";
import { ComedianDTO } from "../../../objects/class/comedian/comedian.interface";
import { Show } from "../../../objects/class/show/Show";
import { Club } from "../../../objects/class/club/Club";
const { db } = getDB()

export async function scrapeShow(showId: number, headless?: boolean): Promise<string> {
    const startDate = new Date();
    console.log(`Started scraping job for ${showId} at ${startDate}`);

    return db.shows.getById(showId)
        .then(async (show: Show) => {
            const club = await db.clubs.getById(show.clubId)
            return runScraper(club, show, headless)
        })
        .then((scrapingOutput: ScrapingOutput) => storeOutputInstance(scrapingOutput))
        .then(() => {

            const diffInMilliseconds = Math.abs(new Date().getTime() - startDate.getTime());

            const minutes = Math.floor(diffInMilliseconds / 60000);
            const seconds = Math.floor((diffInMilliseconds % 60000) / 1000);
            const message = `Finished scraping ${showId} in ${minutes} minutes and ${seconds} seconds.`;

            console.log(message)
            return message
        });
};


const runScraper = async (
    club: Club,
    show: Show,
    headless?: boolean,
): Promise<ScrapingOutput> => {
    return playwright.chromium
        .launch({ headless: headless ?? false })
        .then((browser) => createScrapingFunction(club, show.ticketLink, browser));
};

const createScrapingFunction = (
    club: Club,
    url: string,
    browser: playwright.Browser,
): Promise<ScrapingOutput> => {
    switch (club.name) {
        case ComedyClub.ComedyCellarNewYork:
            return new ComedyCellar(club, browser).scrapeShow();
        case ComedyClub.NewYorkComedyClubUpperWestSide:
            return new NewYorkComedyClub(club, browser).scrapeShow(url);
        case ComedyClub.NewYorkComedyClubMidtown:
            return new NewYorkComedyClub(club, browser).scrapeShow(url);
        case ComedyClub.NewYorkComedyClubEastVillage:
            return new NewYorkComedyClub(club, browser).scrapeShow(url);
        case ComedyClub.TheStand:
            return new TheStand(club, browser).scrapeShow();
        case ComedyClub.TheGrislyPear:
            return new TheGrislyPear(club, browser).scrapeShow(url);
        case ComedyClub.TheTinyCupboard:
            return new TheTinyCupboard(club, browser).scrapeShow(url);
        case ComedyClub.UnionHall:
            return new UnionHall(club, browser).scrapeShow(url);
        case ComedyClub.WilliamsburgComedyClub:
            return new WilliamsburgComedyClub(club, browser).scrapeShow(url);
        case ComedyClub.Rodneys:
            return new Rodneys(club, browser).scrapeShow(url);
        case ComedyClub.EastvilleComedyClubBrooklyn:
            return new EastvilleComedyClub(club, browser).scrapeShow(url);
        case ComedyClub.ComedyVillage:
            return new ComedyVillage(club, browser).scrapeShow(url);
        case ComedyClub.Caveat:
            return new Caveat(club, browser).scrapeShow(url);
        case ComedyClub.WestSideComedyClub:
            return new WestSideComedyClub(club, browser).scrapeShow(url);
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

