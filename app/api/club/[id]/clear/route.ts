import { NextRequest, NextResponse } from "next/server";
import { getDB } from "../../../../../database";
import { QueryHelper } from "../../../../../objects/class/query/QueryHelper";
import { RestApiAction } from "../../../../../objects/enum";
const { database } = getDB();


export async function DELETE(
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {

    QueryHelper.executeAction(RestApiAction.Delete)
    return NextResponse.json({}, { status: 200 })



}
