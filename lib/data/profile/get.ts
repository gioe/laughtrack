import { db } from "@/lib/db";
const getProfileData = (id: number) => {
    return db.user.findUnique({
        where: {
            id: id,
        },
        select: {
            id: true,
            email: true,
            role: true,
            zipCode: true,
        },
    });
};
