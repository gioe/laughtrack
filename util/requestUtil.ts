import { SearchParams } from "../interfaces";
import { ReadonlyHeaders } from "next/dist/server/web/spec-extension/adapters/headers";

export const extractSearchParams = (headers: ReadonlyHeaders): SearchParams => {
    return {
        page: headers.get("page") as string,
        query: headers.get("query") as string,
        sort: headers.get("sort") as string,
        rows: headers.get("rows") as string,
    };
};
