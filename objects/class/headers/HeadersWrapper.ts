

import { ReadonlyHeaders } from "next/dist/server/web/spec-extension/adapters/headers";
import { HeaderKey } from "../../enum";

export class HeadersWrapper {
    // Properties
    headers: ReadonlyHeaders;

    // Constructor
    constructor(headers: ReadonlyHeaders) {
        console.log(headers)
        this.headers = headers
    }

    getValue(key: string) {
        return this.headers.get(key)
    }


    getPath() {
        return this.getValue(HeaderKey.PATH)?.replaceAll("/", "")
    }
}
