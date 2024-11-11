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
    "div.popover-event-container > div.event-single > div.event-info.clearfix > div.clearfix > a";
const NEXT = "div.calendar-next-btn > a";
const DATE_TIME = "p.event-page-date";
const COMEDIAN_NAME = "p.comedian-name > a";
const SHOW_NAME = "div.col-sm-12.text-center > h1";
const PRICE = "div.ticket-info-container > div.ticket-price";
const SEPARATOR = " - ";

export class WestSideComedyClub implements ClubScraper {
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
                console.log(`Error scraping West Side Comedy Club: ${error}`);
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
            .then(() => {
                return this.scraper.scrape({
                    comedianNameLocator: page.locator(COMEDIAN_NAME),
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
            date_time: new DateTimeContainer(
                output[1],
                SEPARATOR,
            ).asDateObject(),
            ticket: {
                link: generateValidUrl(this.clubData.scrapingPageUrl, url),
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
