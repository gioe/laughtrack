import {
    ClubScraper,
    ScrapingOutput,
} from "../../../objects/interfaces";
import { PageManager } from "../handlers/PageManager";
import playwright from "playwright-core";
import { ShowScraper } from "../scrapers/ShowScraper";
import { generateValidUrl } from "../../../util/primatives/urlUtil";
import { DateTimeContainer } from "../containers/DateTimeContainer";
import { delay } from "../../../util/promiseUtil";
import { Show } from "../../../objects/classes/show/Show";
import { ClubInterface } from "../../../objects/classes/club/club.interface";
import { ComedianDTO } from "../../../objects/classes/comedian/comedian.interface";

const LINK =
    "a.MuiTypography-root.MuiTypography-body.MuiLink-root.MuiLink-underlineAlways.css-2p1ku6";
const MORE =
    "div.MuiGrid-root.MuiGrid-item.MuiGrid-grid-xs-12.css-15j76c0 > div.MuiBox-root.css-y3gv0i > button.MuiButton-root.MuiButton-text.MuiButton-textPrimary.MuiButton-sizeMedium.MuiButton-textSizeMedium.MuiButtonBase-root.css-t7zduo > span.MuiTouchRipple-root.css-w0pj6f";
const DATE_TIME =
    "#root > div > div.main.MuiBox-root.css-0 > div > div.MuiGrid-root.MuiGrid-item.MuiGrid-grid-xs-12.MuiGrid-grid-md-8.css-efwuvd > div > div.MuiBox-root.css-1i8t0k4 > span";
const COMEDIAN_NAME =
    "div.MuiBox-root.css-svv1h6 > span.MuiTypography-root.MuiTypography-body.css-16ut9zt";
const SHOW_NAME =
    "#root > div > div.main.MuiBox-root.css-0 > div > div.MuiGrid-root.MuiGrid-item.MuiGrid-grid-xs-12.MuiGrid-grid-md-8.css-efwuvd > div > div.MuiBox-root.css-10dy3fq > span";
const PRICE = "div.event-ticket-type > span.ticket-price.original";

export class Caveat implements ClubScraper {
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
                console.log(`Error scraping Caveat: ${error}`);
                return [];
            });
    };

    runClubScrapingFunction = async (
        page: playwright.Page,
    ): Promise<ScrapingOutput[]> => {
        const moreLocator = page.locator(MORE);
        return this.pageManager
            .expandPage(page, moreLocator)
            .then((page) => {
                const linksLocator = page.locator(LINK);
                return this.pageManager.getAllLinksOnPage(
                    page.url(),
                    linksLocator,
                );
            })
            .then((links: string[]) => this.runScrapingLoop(page, links));
    };

    runScrapingLoop = async (
        page: playwright.Page,
        links: string[],
    ): Promise<ScrapingOutput[]> => {
        const scrapingOutput: ScrapingOutput[] = [];

        for (let index = 0; index < links.length - 1; index++) {
            const input = links[index];
            const output = await this.navigateToUrlAndScrape(page, input);
            scrapingOutput.push(output);
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
            .then(() => delay(2000))
            .then(() => {
                return this.scraper.scrape({
                    comedianNameLocator: page.locator(COMEDIAN_NAME),
                    dateTimeLocator: page.locator(DATE_TIME),
                    showNameLocator: page.locator(SHOW_NAME),
                    priceLocator: page.locator(PRICE),
                });
            })
            .then((scrapingOutput: unknown[]) =>
                this.processOutput(scrapingOutput, link),
            );
    };

    processOutput = (output: unknown[], link: string): ScrapingOutput => {
        const show = new Show({
            lineup: output[0] as ComedianDTO[],
            date_time: new DateTimeContainer(output[1] as string[]).asDateObject(),
            ticket_link: generateValidUrl(this.clubData.baseUrl, link),
            name: output[3] as string,
            price: output[4] as string,
            club_id: this.clubData.id,
        });

        return {
            show: show.asShowDTO(),
            comedians: show.asComedianDTOArray(),
        } as ScrapingOutput;
    };
}
