import {
    ClubScraper,
    ScrapingOutput,
} from "../../../objects/interfaces";
import { PageManager } from "../handlers/PageManager";
import playwright from "playwright-core";
import { ShowScraper } from "../scrapers/ShowScraper";
import { generateValidUrl } from "../../../util/primatives/urlUtil";
import { DateTimeContainer } from "../containers/DateTimeContainer";
import { ClubInterface } from "../../../objects/classes/club/club.interface";
import { Show } from "../../../objects/classes/show/Show";

const ALL_LINKS =
    "div.tribe-events-c-small-cta.tribe-common-b3.tribe-events-calendar-list__event-cost > a";
const NEXT =
    "li.tribe-events-c-nav__list-item.tribe-events-c-nav__list-item--next > a";
const DATE_TIME =
    "div.tribe-events-schedule.tribe-clearfix > h2 > span.tribe-event-date-start";
const SHOW_NAME = "h1.tribe-events-single-event-title";
const PRICE = "span.tribe-amount";
const SEPARATOR = " @ ";

export class ComedyVillage implements ClubScraper {
    private clubData: ClubInterface;
    private browser: playwright.Browser;
    private pageManager = new PageManager();
    private scraper = new ShowScraper();

    constructor(clubData: ClubInterface, browser: playwright.Browser) {
        this.clubData = clubData;
        this.browser = browser;
    }

    scrape = async (): Promise<ScrapingOutput[]> => {
        return this.browser
            .newPage()
            .then((page: playwright.Page) =>
                this.pageManager.navigateToUrl(
                    page,
                    this.clubData.scrapingPageUrl,
                ),
            )
            .then((page: playwright.Page) => this.runClubScrapingFunction(page))
            .catch((error) => {
                console.log(`Error scraping Comedy Village: ${error}`);
                return [];
            });
    };


    scrapeShow = async (url: string): Promise<ScrapingOutput> => {
        return this.browser
            .newPage()
            .then((page: playwright.Page) =>
                this.navigateToUrlAndScrape(page, url)
            )
    }


    runClubScrapingFunction = async (
        page: playwright.Page,
    ): Promise<ScrapingOutput[]> => {
        return this.pageManager
            .getLinksAcrossPages(page, NEXT, ALL_LINKS)
            .then((links: string[]) => this.runScrapingLoop(page, links));
    };

    runScrapingLoop = async (
        page: playwright.Page,
        links: string[],
    ): Promise<ScrapingOutput[]> => {
        const scrapingOutput: ScrapingOutput[] = [];

        for (let index = 0; index < links.length - 1; index++) {
            const input = links[index];
            const show = await this.navigateToUrlAndScrape(page, input);
            scrapingOutput.push(show);
        }

        await this.browser.close();
        return scrapingOutput;
    };

    navigateToUrlAndScrape = async (
        page: playwright.Page,
        link: string,
    ): Promise<ScrapingOutput> => {
        return this.pageManager
            .navigateToUrl(page, link)
            .then((page) => {
                return this.scraper.scrape({
                    dateTimeLocator: page.locator(DATE_TIME),
                    showNameLocator: page.locator(SHOW_NAME),
                    priceLocator: page.locator(PRICE),
                });
            })
            .then((scrapingOutput: any[]) =>
                this.processOutput(scrapingOutput, link),
            );
    };

    processOutput = (output: any[], url: string): ScrapingOutput => {
        const show = new Show({
            lineup: output[0],
            date: new DateTimeContainer(
                output[1],
                SEPARATOR,
            ).asDateObject(),
            ticket: {
                link: generateValidUrl(this.clubData.website, url),
                price: output[4] as number
            },
            name: output[3],
            club_id: this.clubData.id,
        });
        return {
            show: show.asShowDTO(),
            comedians: show.asComedianDTOArray(),
        } as ScrapingOutput;
    };
}
