import { ScrapableScraper } from "./ScrapableScraper.js";
import { Scrapable } from "../../../common/interfaces/scrapable.interface.js";
import { checkForFileExistence } from "../../../common/util/fileSystemUtil.js";

export class ImageScraper {

  private scraper = new ScrapableScraper();

  getScreenshotOfElement = async (
    directory: string,
    fileName: string,
    scrapable?: Scrapable,
    selector?: string): Promise<void> => {

      const fullPath = `images/${directory}/${fileName}.png`;

      if (!checkForFileExistence(fullPath)) {
        return this.scraper.takeScreenshot(fullPath, scrapable, selector)
      }
  }

}
