'use server';


import { NextResponse } from "next/server";
import { runScrapingJob } from "../../../jobs/scrape";

export async function POST() {
    return runScrapingJob()
        .then(() => NextResponse.json({ success: true }, { status: 200 }))
        .catch((error: Error) => {
            console.error(error)
            return NextResponse.json({ message: error }, { status: 500 })
        })

}
