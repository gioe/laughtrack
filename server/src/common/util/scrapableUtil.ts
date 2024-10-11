import playwright from "playwright-core";
import { Scrapable } from "../models/interfaces/scrape.interface.js";

export const generateCompleteUrl = (scrapable: Scrapable, path: string): string => {
	if (pathIsCompleteUrl(path)) return path
	const page = scrapable as playwright.Page;
    const pageOrigin = new URL(page.url()).origin;
	return `${pageOrigin}${path}`
}

export const generateUrlsFromPaths = (scrapable: Scrapable, paths: string[]): string[] => {
	return paths.map(path => generateCompleteUrl(scrapable, path))
}

export const pathIsCompleteUrl = (path: string) => {
	try {
		const url = new URL(path);
		return true
	 } catch {
		return false
	 }
}

