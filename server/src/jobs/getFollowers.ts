import playwright from "playwright";
import * as comedianController from '../api/controllers/comedian/index.js'
import { GetComedianDetailsOutput } from '../api/dto/comedian.dto.js';
import { delay, runTasks } from '../common/util/promiseUtil.js';
import { generateLocalDBConnection } from '../database/config.js';
import { ComedianInterface } from "../common/interfaces/comedian.interface.js";

async function getFollowers() {
    generateLocalDBConnection()
        .then(() => comedianController.getAllComedians())
        .then((comedians: ComedianInterface[]) => fetchAndSetFollowers(comedians))
}

const fetchAndSetFollowers = async (comedians: ComedianInterface[]): Promise<any> => {
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



const fetchAndSetFollower = async (page: playwright.Page, comedian: ComedianInterface): Promise<void> => {
    const url = `https://www.instagram.com/${comedian.instagramAccount}/?hl=en`
    const followersLink = `${comedian.instagramAccount}/followers/?hl=en`
    
    await page.goto(url)
    await page.screenshot({ path: `${comedian.name}.png`, fullPage: true});
}

getFollowers();
