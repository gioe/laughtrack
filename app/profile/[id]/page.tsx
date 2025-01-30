"use server";

import { auth } from "@/auth";
import { StyleContextProvider } from "@/contexts/StyleProvider";
import { APIRoutePath, StyleContextKey } from "@/objects/enum";
import Navbar from "@/ui/components/navbar";
import UserDetailHeader from "@/ui/pages/entity/user/detailheader";
import FooterComponent from "@/ui/pages/home/footer";
import { makeRequest } from "@/util/actions/makeRequest";
import { ProfilePageResponse } from "./interface";

export default async function Page(props: { params: Promise<{ id: string }> }) {
    const session = await auth();

    const { profile } = await makeRequest<ProfilePageResponse>(
        APIRoutePath.Profile,
        {
            session,
        },
    );

    return (
        <main className="min-h-screen w-full bg-ivory">
            <StyleContextProvider initialContext={StyleContextKey.Search}>
                <Navbar currentUser={session?.user} />
                <UserDetailHeader userProfile={profile} session={session} />
            </StyleContextProvider>

            <FooterComponent />
        </main>
    );
}
