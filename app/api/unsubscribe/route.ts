
import jwt from "jsonwebtoken";
import { db } from "@/lib/db";
import { NextResponse } from "next/server";

export async function POST(request: Request) {
    try {
        const { token } = await request.json();
        // Verify token - this will throw an error if token is invalid or expired
        const decoded = jwt.verify(token, process.env.SECRET_KEY!) as {
            email: string;
            type: string;
            exp: number;
            iat: number;
        };
        // Token is valid! We can trust that this request is from the owner of this email
        const userEmail = decoded.email;

        // Update the database
        await db.user.update({
            where: {
              email: userEmail
            },
            data: {
              profile: {
                update: {
                  emailShowNotifications: false
                }
              }
            }
          });

        return NextResponse.json({ success: true });
    } catch (error) {
        if (error instanceof jwt.TokenExpiredError) {
            return NextResponse.json(
                { error: 'This unsubscribe link has expired. Please request a new one.' },
                { status: 401 }
            );
        }
        console.log(error)
        return NextResponse.json(
            { error: 'Invalid unsubscribe link' },
            { status: 400 }
        );
    }
}
