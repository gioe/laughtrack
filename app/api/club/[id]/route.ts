import * as clubController from "../../../../controllers/club"
import { NextRequest, NextResponse } from 'next/server';
import { sortShows } from "../../../../util/domainModels/show/sort";
import { filterShows } from "../../../../util/domainModels/show/filter";
import { toPaginatedData } from "../../../../util/domainModels/pagination/mapper";
import { extractSearchParams } from "../../../../util/requestUtil";
import { headers } from 'next/headers'

export async function GET(
    req: NextRequest,
    { params }: { params: Promise<{ slug: string }> }
) {
    const headersList = await headers()

    const slug = (await params).slug // 'a', 'b', or 'c'

    const { sort, query, page, rows } = extractSearchParams(headersList)

    const decodedName = decodeURI(slug)

    const result = await clubController.getByName(decodedName)
    var dates = result?.dates ?? []

    if (sort) {
        dates = sortShows(dates, sort)
    }

    dates = filterShows(dates, {
        name: query
    })

    const paginationData = toPaginatedData(dates, page, rows)

    return NextResponse.json({
        entity: {
            name: slug,
            socialData: result?.socialData,
            dates: paginationData.data
        },
        totalShows: dates.length,
        totalPages: paginationData.totalPages
    }, {
        status: 200,
    })
}