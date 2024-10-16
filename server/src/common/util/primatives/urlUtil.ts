import { stringIsAValidUrl } from "./stringUtil.js"
import playwright from "playwright-core";

export const generateValidUrls = (url: string, hrefs: string[]) => {
    return hrefs.map((link: string) => generateValidUrl(url, link))
	.filter((url: string) => stringIsAValidUrl(url))
	.filter((url: string) => !url.includes('fcomedyclub'))
}

export const generateValidUrl = (url: string, href: string) => {
    return toUrl(url, href)
}

export const toUrl = (url: string, href: string): string => {
	if (pathIsCompleteUrl(href)) return href

    const pageOrigin = new URL(url).origin;
	return `${pageOrigin}${href}`

}

export const pathIsCompleteUrl = (href: string) => {
	try {
		const url = new URL(href);
		return true
	 } catch {
		return false
	 }
}

export const isEventbritePage = (page: playwright.Page): boolean => {
    const basePageUrl = page.url()
    return basePageUrl.includes('eventbrite')
}
