import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { URLParam } from "../enum";
import { stringIsAValidUrl } from "./stringUtil";
import playwright from "playwright-core";

export const generateValidUrls = (url: string, hrefs: string[]) => {
    return hrefs
        .map((link: string) => generateValidUrl(url, link))
        .filter((url: string) => stringIsAValidUrl(url))
        .filter((url: string) => !url.includes("fcomedyclub"));
};

export const generateValidUrl = (url: string, href: string) => {
    return toUrl(url, href);
};

export const toUrl = (url: string, href: string): string => {
    if (pathIsCompleteUrl(href)) return href;

    const pageOrigin = new URL(url).origin;
    return `${pageOrigin}${href}`;
};

export const pathIsCompleteUrl = (href: string) => {
    try {
        const url = new URL(href);
        return true;
    } catch {
        return false;
    }
};

export const isEventbritePage = (page: playwright.Page): boolean => {
    const basePageUrl = page.url();
    return basePageUrl.includes("eventbrite");
};

export const generateUrl = (path: string): string => {
    return process.env.URL_DOMAIN + path;
};

export function handleUrlParams(
    param: URLParam,
    value: string | number,
) {

    const stringParam = value.toString();
    const searchParams = new URLSearchParams(useSearchParams());

    switch (param) {
        case URLParam.Sort, URLParam.Query, URLParam.Rows, URLParam.Page: addOrRemoveSingleValue(searchParams, param, stringParam);
        default: addOrRemoveCommaSeparatedValue(searchParams, param, stringParam);
    }
}

const addOrRemoveSingleValue = (
    params: URLSearchParams,
    param: string,
    value: string,
) => {
    const { replace } = useRouter();
    const pathname = usePathname();

    if (value) params.set(param, value);
    else params.delete(param);

    replace(`${pathname}?${params.toString()}`);

};

const addOrRemoveCommaSeparatedValue = (
    params: URLSearchParams,
    param: string,
    value: string,
) => {

    const { replace } = useRouter();
    const pathname = usePathname();
    const filters = params.get(param);
    let allValues = filters?.split(",") ?? [];
    const valueIncluded = allValues.includes(value);

    if (!valueIncluded) {
        allValues.push(value);
    } else {
        allValues = allValues.filter(
            (paramValues: string) => paramValues !== value,
        );
    }

    if (allValues.length > 0) {
        params.set(param, allValues.join(","));
    } else {
        params.delete(param);
    }

    replace(`${pathname}?${params.toString()}`);
};
