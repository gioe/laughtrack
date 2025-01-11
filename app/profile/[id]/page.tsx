"use server";

import { FullRoundedButton } from "../../../components/button/rounded/full";
import { db } from "../../../lib/db";

const getPageData = (id: number) => {
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

export default async function Page(props: { params: Promise<{ id: string }> }) {
    const params = await props.params;
    const user = await getPageData(Number(params.id));

    return (
        <main className="flex-grow pt-24 bg-ivory">
            <section className="max-w-7xl mx-auto text-left ml-5">
                <h2 className="font-fjalla text-5xl text-copper p-5">
                    Personal details
                </h2>
                {user?.email}
            </section>
            <section className="max-w-7xl mx-auto text-left ml-5">
                <FullRoundedButton label="Update" />
            </section>
        </main>
    );
}
