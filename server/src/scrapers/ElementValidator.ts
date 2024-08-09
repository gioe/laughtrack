import ValidationRules from '../types/validationRules.interface.js';
import Scrapable from '../types/scrapable.interface.js';
import { runTasks } from '../util/types/promiseUtil.js';
import { ElementCounter } from './ElementCounter.js';
import { ElementScaper } from './ElementScaper.js';

export class ElementValidator {

  private elementCounter = new ElementCounter();
  private elementScraper = new ElementScaper();

  validateElements = async (elements: Scrapable[],
    rules: ValidationRules): Promise<Scrapable[]> => {
    
      const tasks = elements.map(element => this.validateElement(element, rules))
      return runTasks(tasks)
    }
  

  validateElement = async (object: Scrapable,
    rules: ValidationRules): Promise<Scrapable> => {
    
      const requiredSelectorTask = this.checkForRequiredSelectors(object, rules.requiredSelectors)
      const invalidValueTask = this.checkforValidValue(object, rules.invalidText)

    return runTasks([requiredSelectorTask, invalidValueTask])
      .then((validations: boolean[]) => {
        return object
      })

    }

    checkForRequiredSelectors = async (element: Scrapable,
      requiredSelectors?: string[]): Promise<boolean> => {
      
        return runTasks([]).then(() => true)
      }

      checkforValidValue = async (element: Scrapable,
        invalidValue?: string): Promise<boolean> => {
          return runTasks([]).then(() => true)
        }
}