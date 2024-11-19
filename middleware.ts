export { auth } from "./auth";


// middleware.js

import { NextRequest, NextResponse } from "next/server";
export async function middleware(request: NextRequest) {
    const requestHeaders = new Headers(request.headers);
    requestHeaders.set("x-pathname", request.nextUrl.pathname);
    return NextResponse.next({
        request,
    });
}
