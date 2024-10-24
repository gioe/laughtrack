import { Locator } from "playwright-core";
import { capitalized } from "../../../common/util/primatives/stringUtil.js";
import { toPrice } from "../../../common/util/primatives/priceUtil.js";
import { Comedian } from "../../../common/models/classes/Comedian.js";
import { runTasks } from "../../../common/util/promiseUtil.js";
import { PageManager } from "../handlers/PageManager.js";
import { ScrapingArgs } from "../../../common/models/interfaces/scrape.interface.js";

export class ShowScraper {

  private pageManager = new PageManager();

  getShowLineup = async (locator?: Locator): Promise<Comedian[]> => {
    return locator == undefined ? [] :
      this.pageManager.getText(locator)
        .then((names: string[]) => names.map((name: string) => new Comedian(name)))
        .catch((error) => {
          console.error(`Error getting show names: ${error}`)
          return []
        })
  }

  getShowDateTime = async (locator?: Locator): Promise<string[]> => {
    return locator == undefined ? [] :
      this.pageManager.getText(locator)
        .catch((error) => {
          console.error(`Error getting show datetime: ${error}`)
          return []
        })
  }

  getTicketLink = async (locator?: Locator): Promise<string> => {
    return locator == undefined ? "" :
      this.pageManager.getHref(locator.first())
        .catch((error) => {
          console.error(`Error getting show ticket link: ${error}`)
          return ""
        })
  }

  getName = async (locator?: Locator): Promise<string> => {
    return locator == undefined ? "" :
      this.pageManager.getTextContent(locator.first())
        .then((name: string) => capitalized(name))
        .catch((error) => {
          console.error(`Error getting show name: ${error}`)
          return ""
        })
  }

  getPrice = async (locator?: Locator): Promise<string> => {
    return locator == undefined ? "0.00" :
      this.pageManager.getTextContent(locator.first())
        .then((price: string) => toPrice(price))
        .catch((error) => {
          console.error(`Error getting price: ${error}`)
          return "0.00"
        })
  }

  scrape = async (args: ScrapingArgs): Promise<any[]> => {
    return runTasks<any>([
      this.getShowLineup(args.comedianNameLocator),
      this.getShowDateTime(args.dateTimeLocator),
      this.getTicketLink(args.ticketLinkLocator),
      this.getName(args.showNameLocator),
      this.getPrice(args.priceLocator)
    ])
  }

}