

import { ReadonlyHeaders } from "next/dist/server/web/spec-extension/adapters/headers";
import { HeaderKey } from "../../enum";
import { getDefaultHeaderValue } from "../../../util/primatives/headerUtil";

export class HeadersWrapper {
    // Properties
    headers: ReadonlyHeaders;
    private static instance: HeadersWrapper;

    static getInstance() {
        if (!HeadersWrapper.instance) {
            HeadersWrapper.instance = new HeadersWrapper();
        }
        return HeadersWrapper.instance;
    }

    static setHeaders(headers: ReadonlyHeaders) {
        this.getInstance().headers = headers
    }

    static async updateHeaders(headers: Promise<ReadonlyHeaders>) {
        return headers.then((value: ReadonlyHeaders) => this.getInstance().headers = value)
    }

    static getValue(key: HeaderKey) {
        return this.getInstance().headers.get(key.valueOf()) ?? getDefaultHeaderValue(key)

    }

    // We're keeping track of the current url path in the request headers.
    // The "base" path is always the element at index 1 and we use this as our query map key.
    static getBasePath() {
        const fullPath = HeadersWrapper.getValue(HeaderKey.Path)
        const pathElements = fullPath.split('/')
        const basePath = pathElements[1];

        // We can't work with an empty string, so for the landing page, we'll hijack and call it home for now.
        if (basePath == '') return 'home'
        else return basePath
    }
}
