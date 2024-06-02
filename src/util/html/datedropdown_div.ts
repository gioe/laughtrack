import puppeteer from 'puppeteer';
import { HTMLConfigurable } from "../../types/configs.interface.js";

export const getDateDropdown = async (page: puppeteer.Page, config: HTMLConfigurable) => {
    return await page.$(config.dateMenuSelector);
}

export const getDateDropdownItemsTextContent = async (dateDropdown: puppeteer.ElementHandle<Element>, config: HTMLConfigurable) => {
    return await dateDropdown.$$eval(config.dateOptionSelector, elements => elements.map(element => element.textContent ?? ""));
  }

  export const getDateDropdownItems = async (page: puppeteer.Page, config: HTMLConfigurable) => {
    return await page.$$eval(config.dateOptionSelector, options =>  options.map(option => option.getAttribute('value') ?? ""));
  }

  export const getSelectedValue = async (page: puppeteer.Page) => {
    return await page.$eval('select#cc_lineup_select_dates', (el: HTMLSelectElement) => el.value);
  }
