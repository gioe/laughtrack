export async function POST(request: Request) {
    try {
        const { token } = await request.json();

        // Verify token - this will throw an error if token is invalid or expired
        const decoded = jwt.verify(token, process.env.JWT_SECRET!) as {
            email: string;
            type: string;
            exp: number;
            iat: number;
        };

        // Token is valid! We can trust that this request is from the owner of this email
        const userEmail = decoded.email;

        // Update the database
        await db.user.update({
            where: { email: userEmail },
            data: { subscribed: false }
        });

        return NextResponse.json({ success: true });
    } catch (error) {
        if (error instanceof jwt.TokenExpiredError) {
            return NextResponse.json(
                { error: 'This unsubscribe link has expired. Please request a new one.' },
                { status: 401 }
            );
        }

        return NextResponse.json(
            { error: 'Invalid unsubscribe link' },
            { status: 400 }
        );
    }
}
