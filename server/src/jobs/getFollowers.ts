import playwright from "playwright";
import * as comedianController from '../api/controllers/comedian/index.js'
import { GetComedianDetailsOutput } from '../api/dto/comedian.dto.js';
import { delay, runTasks } from '../common/util/promiseUtil.js';
import { generateLocalDBConnection } from '../database/config.js';

async function getFollowers() {
    generateLocalDBConnection()
        .then(() => comedianController.getAll())
        .then((comedians: GetComedianDetailsOutput[]) => fetchAndSetFollowers(comedians))
}

const fetchAndSetFollowers = async (comedians: GetComedianDetailsOutput[]): Promise<any> => {
    const page = await playwright.chromium.launch({ headless: false })
        .then(browser => browser.newContext())
        .then(context => context.newPage())

    await page.goto("https://www.instagram.com/accounts/login/")
    await page.getByLabel('Phone number, username, or email').fill(process.env.INSTAGRAM_USERNAME ?? "");
    await page.getByLabel('Password').fill(process.env.INSTAGRAM_PASSWORD ?? "");
    await page.getByText('Log in', { exact: true } ).click();

    const firstComedian = comedians[0]
    fetchAndSetFollower(page, firstComedian)

    // const tasks = comedians.map((comedian: GetComedianDetailsOutput) => fetchAndSetFollower(comedian));
    // return runTasks(tasks)
}



const fetchAndSetFollower = async (page: playwright.Page, comedian: GetComedianDetailsOutput): Promise<void> => {
    const url = `https://www.instagram.com/${comedian.instagram_account}/?hl=en`
    const followersLink = `${comedian.instagram_account}/followers/?hl=en`
    const href = `[href*="/${followersLink}"]`
    
    await page.goto(url)
    await page.screenshot({ path: `${comedian.name}.png`, fullPage: true});
}

getFollowers();
