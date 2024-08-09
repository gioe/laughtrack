import { ElementScaper } from './ElementScaper.js';
import Scrapable from '../types/scrapable.interface.js';
import { Comedian } from '../classes/Comedian.js';

export class ShowDetailPageScraper {

  private elementScraper = new ElementScaper()
  
  scrape = async (scrapable: Scrapable): Promise<Comedian[][]> => {
    return []
  }


}