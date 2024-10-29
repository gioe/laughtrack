import { NextRequest, NextResponse } from 'next/server';
import { generateToken, verifyToken } from '../../../../util/domainModels/token';
import { headers } from 'next/headers'

export async function POST(
    req: NextRequest) {

    const headersList = await headers()
    const authHeader = headersList.get('authorization')

    const refreshToken = authHeader && authHeader.split(' ')[1];  // Bear

    if (!refreshToken) {
        return NextResponse.json({
            messsage: "Refresh token not provided"
        }, {
            status: 401,
        })
    }

    try {
        const payload = verifyToken(refreshToken);
        const accessToken = generateToken({ id: payload.id, email: payload.email }, "access");
        
        return NextResponse.json(accessToken, {
            status: 200,
        })
    }

    catch (err) {
        return NextResponse.json(err, {
            status: 403,
        })
    }


}