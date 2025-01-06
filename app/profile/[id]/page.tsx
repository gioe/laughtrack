"use server";

import { FullRoundedButton } from "../../../components/button/rounded/full";
import { getDB } from "../../../database";
const { database } = getDB();

const getPageData = (id: number) => {
    return database.page.getProfileData(id);
};

export default async function Page(props: { params: Promise<{ id: string }> }) {
    const params = await props.params;
    const { response } = await getPageData(Number(params.id));
    console.log(response);

    return (
        <main className="flex-grow pt-24 bg-ivory">
            <section className="max-w-7xl mx-auto text-left ml-5">
                <h2 className="font-fjalla text-5xl text-copper p-5">
                    Personal details
                </h2>
            </section>
            <section className="max-w-7xl mx-auto text-left ml-5">
                <FullRoundedButton label="Update" />
            </section>
        </main>
    );
}
