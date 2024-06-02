import puppeteer from 'puppeteer';
import { ClubConfig } from "../types/index.js";

export const getDateDropdown = async (page: puppeteer.Page, config: ClubConfig) => {
    return await page.$(config.htmlConfig.dateMenuSelector);
}

export const getDateDropdownItemsTextContent = async (dateDropdown: puppeteer.ElementHandle<Element>, config: ClubConfig) => {
    return await dateDropdown.$$eval(config.htmlConfig.dateOptionSelector, elements => elements.map(element => element.textContent ?? ""));
  }

  export const getDateDropdownItems = async (page: puppeteer.Page, config: ClubConfig) => {
    return await page.$$eval(config.htmlConfig.dateOptionSelector, options =>  options.map(option => option.getAttribute('value') ?? ""));
  }

  export const getSelectedValue = async (page: puppeteer.Page) => {
    return await page.$eval('select#cc_lineup_select_dates', (el: HTMLSelectElement) => el.value);
  }
