import playwright, { Locator, Page } from "playwright-core";
import {
    generateValidUrl,
    generateValidUrls,
} from "../../../util/primatives/urlUtil";
import { removeBadWhiteSpace } from "../../../util/primatives/stringUtil";
import { delay } from "../../../util/promiseUtil";

export class PageManager {
    getAllLinksOnPage = async (
        url: string,
        locator: playwright.Locator,
    ): Promise<string[]> => {
        return this.getAllHrefs(locator).then((hrefs: string[]) =>
            generateValidUrls(url, hrefs),
        );
    };

    getLinksAcrossPages = async (
        page: Page,
        nextSelector: string,
        allSelector: string,
        allPageLinks?: string[],
        allScrapedLinks?: string[],
    ): Promise<string[]> => {
        const pageLinks = allPageLinks ?? [];
        const scrapedLinks = allScrapedLinks ?? [];
        const linkLocator = page.locator(allSelector);
        const nextPageLinkLocator = page.locator(nextSelector).first();

        return this.getAllLinksOnPage(page.url(), linkLocator)
            .then((links: string[]) => {
                scrapedLinks.push(...links);
                return this.getHref(nextPageLinkLocator);
            })
            .then((href: string) => generateValidUrl(page.url(), href))
            .then((link: string) => {
                if (!pageLinks.includes(link)) {
                    pageLinks.push(link);
                    return this.navigateToUrl(page, link);
                }
                throw new Error(
                    "Page is already in the link list. Breaking loop",
                );
            })
            .then((page: Page) =>
                this.getLinksAcrossPages(
                    page,
                    nextSelector,
                    allSelector,
                    pageLinks,
                    scrapedLinks,
                ),
            )
            .catch((error) => {
                console.warn(error);
                return [...new Set(scrapedLinks)];
            });
    };

    selectDateOption = async (locator: Locator, option: string) => {
        return locator.first().selectOption(option);
    };

    navigateToUrl = async (page: Page, input: string): Promise<Page> => {
        return page.goto(input).then(() => page);
    };

    expandPage = async (page: Page, locator: Locator): Promise<Page> => {
        return locator
            .isVisible()
            .then((visible: boolean) => {
                if (visible) return locator.first().click();
                throw new Error(
                    "Button not visible. No reason to try to click.",
                );
            })
            .then(() => delay(1000))
            .then(() => this.expandPage(page, locator))
            .catch((error) => {
                console.warn(error);
                return page;
            });
    };

    select = async (
        page: Page,
        selector: string,
        option: string,
    ): Promise<Page> => {
        return page.selectOption(selector, option).then(() => page);
    };

    clickPageButton = async (page: Page, locator: Locator): Promise<Page> => {
        return locator
            .isVisible()
            .then((visible: boolean) => {
                if (visible) return locator.first().click();
                throw new Error(
                    "Button not visible. No reason to try to click.",
                );
            })
            .then(() => delay(1000))
            .then(() => page);
    };

    getText = async (locator: Locator): Promise<string[]> => {
        const values: string[] = [];
        for (const element of await locator.all()) {
            const value = await this.getTextContent(element);
            values.push(value);
        }
        return values;
    };

    getValues = async (locator: Locator): Promise<string[]> => {
        const values: string[] = [];
        for (const element of await locator.all()) {
            const value = await this.getValue(element);
            values.push(value);
        }
        return values;
    };

    getAllHrefs = async (locator: playwright.Locator): Promise<string[]> => {
        const hrefs: string[] = [];
        for (const element of await locator.all()) {
            const href = await this.getHref(element);
            hrefs.push(href);
        }
        return hrefs;
    };

    getHref = async (locator: playwright.Locator): Promise<string> => {
        await locator.waitFor({ state: "attached", timeout: 1000 });
        return locator
            .getAttribute("href", { timeout: 1000 })
            .then((href) => (href ? removeBadWhiteSpace(href) : ""));
    };

    getValue = async (locator: playwright.Locator): Promise<string> => {
        await locator.waitFor({ state: "attached", timeout: 1000 });
        return locator
            .getAttribute("value", { timeout: 1000 })
            .then((value) => (value ? removeBadWhiteSpace(value) : ""));
    };

    getTextContent = async (locator: playwright.Locator): Promise<string> => {
        await locator.waitFor({ state: "attached", timeout: 1000 });
        return locator
            .textContent({ timeout: 1000 })
            .then((text: string | null) =>
                text ? removeBadWhiteSpace(text) : "",
            );
    };
}
