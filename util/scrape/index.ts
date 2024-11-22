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
    Grove34
} from "../../jobs/scrape/clubs";
import { StMarksComedyClub } from "../../jobs/scrape/clubs/St. Marks Comedy Club";
import { ClubInterface } from "../../objects/class/club/club.interface";
import { ComedyClub } from "../../objects/enum";
import { ScrapingOutput } from "../../objects/interface";
import playwright from "playwright";


export const clubScrapingFunction = (
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
        case ComedyClub.StMarksComedyClub:
            return new StMarksComedyClub(club, browser).scrape();
        case ComedyClub.Grove34:
            return new Grove34(club, browser).scrape();
        default:
            throw new Error("No club name found");
    }
};

export const showScrapingFunction = (
    club: ClubInterface,
    url: string,
    browser: playwright.Browser,
    pause: boolean
): Promise<ScrapingOutput> => {
    switch (club.name) {
        case ComedyClub.NewYorkComedyClubUpperWestSide:
            return new NewYorkComedyClub(club, browser).scrapeShow(url, pause);
        case ComedyClub.NewYorkComedyClubMidtown:
            return new NewYorkComedyClub(club, browser).scrapeShow(url, pause);
        case ComedyClub.NewYorkComedyClubEastVillage:
            return new NewYorkComedyClub(club, browser).scrapeShow(url, pause);
        case ComedyClub.TheGrislyPear:
            return new TheGrislyPear(club, browser).scrapeShow(url, pause);
        case ComedyClub.TheTinyCupboard:
            return new TheTinyCupboard(club, browser).scrapeShow(url, pause);
        case ComedyClub.UnionHall:
            return new UnionHall(club, browser).scrapeShow(url, pause);
        case ComedyClub.WilliamsburgComedyClub:
            return new WilliamsburgComedyClub(club, browser).scrapeShow(url, pause);
        case ComedyClub.Rodneys:
            return new Rodneys(club, browser).scrapeShow(url, pause);
        case ComedyClub.EastvilleComedyClubBrooklyn:
            return new EastvilleComedyClub(club, browser).scrapeShow(url, pause);
        case ComedyClub.ComedyVillage:
            return new ComedyVillage(club, browser).scrapeShow(url, pause);
        case ComedyClub.Caveat:
            return new Caveat(club, browser).scrapeShow(url, pause);
        case ComedyClub.WestSideComedyClub:
            return new WestSideComedyClub(club, browser).scrapeShow(url, pause);
        case ComedyClub.Grove34:
            throw new Error(`Not possible to scape page urls individually on this club`)
        case ComedyClub.ComedyCellarNewYork:
            throw new Error(`Not possible to scape page urls individually on this club`)
        case ComedyClub.TheStand:
            throw new Error(`Not possible to scape page urls individually on this club`)
        default:
            throw new Error("No club name found");
    }
};

