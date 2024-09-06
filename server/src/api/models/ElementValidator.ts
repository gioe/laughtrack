import { ValidationRules} from '../../@types/ValidationRules.js';
import { runTasks } from '../../util/promiseUtil.js';
import { ElementCounter } from './ElementCounter.js';
import { removeBadWhiteSpace } from '../../util/stringUtil.js';
import { ElementHandle } from "playwright";
import { ElementHandler } from './ElementHandler.js';

export class ElementValidator {

  private elementCounter = new ElementCounter();
  private elementHandler = new ElementHandler();

  filterInvalidElements = async (elementHandles: ElementHandle<Element>[], rules: ValidationRules): Promise<ElementHandle<Element>[]> => {
    const tasks = elementHandles.map(elementHandle => this.filterInvalidElement(elementHandle, rules))
    return runTasks(tasks)
    .then((values: (ElementHandle<Element> | undefined)[]) => {
      return values.filter(value => value !== undefined) as ElementHandle<Element>[]
    })
  }

  filterInvalidElement = async (elementHandle: ElementHandle<Element>, rules: ValidationRules): Promise<Promise<ElementHandle<Element> | undefined>> => {
    return this.validateElement(elementHandle, rules).then((valid: boolean) =>  valid ? elementHandle : undefined)
  }

  validateElement = async (elementHandle: ElementHandle<Element>,
    rules: ValidationRules
  ): Promise<boolean> => {

    const requiredSelectorTask = this.checkForRequiredSelectors(elementHandle, rules.requiredSelectors)
    const invalidValueTask = this.checkforValidTextValue(elementHandle, rules.invalidText)

    return runTasks([requiredSelectorTask, invalidValueTask])
      .then((validations: boolean[]) => validations.filter(validation => validation == false).length == 0)
  }

  checkForRequiredSelectors = async (elementHandle: ElementHandle<Element>,
    requiredSelectors?: string[]): Promise<boolean> => {
    if (requiredSelectors) {
      const validationTasks = requiredSelectors.map(selector => this.elementCounter.getElementCount(elementHandle, selector))
      return runTasks(validationTasks).then((counts: number[]) => counts.includes(0))
    }
    return true
  }

  checkforValidTextValue = async (elementHandle: ElementHandle<Element>,
    invalidTextValue?: string): Promise<boolean> => {
    if (invalidTextValue) {
      return this.elementHandler.getTextContent(elementHandle)
        .then((textContent: string) => removeBadWhiteSpace(textContent) != invalidTextValue)
    }
    return true;
  }
}