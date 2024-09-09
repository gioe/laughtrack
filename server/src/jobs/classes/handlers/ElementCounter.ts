import { Scrapable } from '../../../common/interfaces/scrapable.interface.js';
import { provideGenericPromiseResponse } from '../../../common/util/promiseUtil.js';

export class ElementCounter {

  getElementCount = async (scrapable: Scrapable,
    selector?: string): Promise<number> => {
      if (selector) {
      return scrapable.$$eval(selector, (e: Element[]) => e.length)
        .then((count: number) => count)
    }
    
    return provideGenericPromiseResponse(0)
  }
  
}