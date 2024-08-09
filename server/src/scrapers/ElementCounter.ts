import { provideGenericPromiseResponse, runTasks } from '../util/types/promiseUtil.js';
import Scrapable from '../types/scrapable.interface.js';

export class ElementCounter {

  getElementCount = async (object: Scrapable,
    selector?: string): Promise<number> => {
    
      if (selector) {
      return object.$$eval(selector, (e: Element[]) => e.length)
        .then((count: number) => count)
    }
    
    return provideGenericPromiseResponse(0)
  }
  
}