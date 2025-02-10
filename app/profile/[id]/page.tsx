"use server";

import { UserProfileResponse } from "@/app/api/profile/[id]/interface";
import { auth } from "@/auth";
import { StyleContextProvider } from "@/contexts/StyleProvider";
import { APIRoutePath, StyleContextKey } from "@/objects/enum";
import Navbar from "@/ui/components/navbar";
import UserDetailHeader from "@/ui/pages/entity/user/header";
import FooterComponent from "@/ui/pages/home/footer";
import { makeRequest } from "@/util/actions/makeRequest";

export default async function ProfilePage(props: {
    params: Promise<{ id: string }>;
}) {
    const id = (await props.params).id;

    const { user } = await makeRequest<UserProfileResponse>(
        APIRoutePath.Profile + `/${id}`,
    );

    return (
        <main className="min-h-screen w-full bg-ivory">
            <StyleContextProvider initialContext={StyleContextKey.Search}>
                <Navbar currentUser={user} />
                <UserDetailHeader userProfile={user} />
            </StyleContextProvider>
            <FooterComponent />
        </main>
    );
}
