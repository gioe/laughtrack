import { Locator } from "playwright-core";
import { capitalized } from "../../../util/primatives/stringUtil";
import { toPrice } from "../../../util/primatives/priceUtil";
import { runTasks } from "../../../util/promiseUtil";
import { PageManager } from "../handlers/PageManager";
import { ScrapingArgs } from "../../../objects/interface";
import { Comedian } from "../../../objects/class/comedian/Comedian";

export class ShowScraper {
    private pageManager = new PageManager();

    getShowLineup = async (locator?: Locator): Promise<Comedian[]> => {
        return locator == undefined
            ? []
            : this.pageManager
                .getText(locator)
                .then((names: string[]) => {
                    return names.map((name: string) => new Comedian({
                        name
                    }))
                })
                .catch((error) => {
                    console.error(`Error getting show names: ${error}`);
                    return [];
                });
    };

    getShowDateTime = async (locator?: Locator): Promise<string[]> => {
        return locator == undefined
            ? []
            : this.pageManager.getText(locator).catch((error) => {
                console.error(`Error getting show datetime: ${error}`);
                return [];
            });
    };

    getTicketLink = async (locator?: Locator): Promise<string> => {
        return locator == undefined
            ? ""
            : this.pageManager.getHref(locator.first()).catch((error) => {
                console.error(`Error getting show ticket link: ${error}`);
                return "";
            });
    };

    getName = async (locator?: Locator): Promise<string> => {
        return locator == undefined
            ? ""
            : this.pageManager
                .getTextContent(locator.first())
                .then((name: string) => capitalized(name))
                .catch((error) => {
                    console.error(`Error getting show name: ${error}`);
                    return "";
                });
    };

    getPrice = async (locator?: Locator): Promise<string> => {
        return locator == undefined
            ? "0.00"
            : this.pageManager
                .getTextContent(locator.first())
                .then((price: string) => toPrice(price))
                .catch((error) => {
                    console.error(`Error getting price: ${error}`);
                    return "0.00";
                });
    };

    scrape = async (args: ScrapingArgs): Promise<unknown[]> => {
        return runTasks<unknown>([
            this.getShowLineup(args.comedianNameLocator),
            this.getShowDateTime(args.dateTimeLocator),
            this.getTicketLink(args.ticketLinkLocator),
            this.getName(args.showNameLocator),
            this.getPrice(args.priceLocator),
        ]);
    };
}
