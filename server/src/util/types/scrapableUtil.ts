import playwright from "playwright";
import { Scrapable } from "../../types/scrapable.interface.js";


export const generateCompleteUrl = (scrapable: Scrapable, path: string): string => {
	const page = scrapable as playwright.Page;
    const pageOrigin = new URL(page.url()).origin;
	return `${pageOrigin}${path}`
}

export const generateUrlsFromPaths = (scrapable: Scrapable, paths: string[]): string[] => {
	return paths.map(path => generateCompleteUrl(scrapable, path))
}


