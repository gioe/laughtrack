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
} from "../../jobs/scrape/clubs";
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
        default:
            throw new Error("No club name found");
    }
};
