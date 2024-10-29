import * as comedianController from "../../../../controllers/comedian"

import { NextRequest, NextResponse } from 'next/server';

export async function POST(
  req: NextRequest) {

    const trendingComedians = await comedianController.getTrendingComedians()

    return NextResponse.json({
      trendingComedians
    }, {
      status: 200,
    })

}

