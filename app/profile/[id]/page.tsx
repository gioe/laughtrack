"use server";

import { auth } from "@/auth";
import { StyleContextProvider } from "@/contexts/StyleProvider";
import { StyleContextKey } from "@/objects/enum";
import Navbar from "@/ui/components/navbar";
import UserDetailHeader from "@/ui/pages/entity/user/header";
import FooterComponent from "@/ui/pages/home/footer";
import { getUserProfileData } from "@/lib/data/profile/getUserProfileData";

export default async function ProfilePage(props: {
    params: Promise<{ id: string }>;
}) {
    const [params, session] = await Promise.all([props.params, auth()]);

    if (!session) {
        return <div>You shouldn't be here.</div>;
    } else {
        const profile = await getUserProfileData(session.profile?.userId);

        return (
            <main className="min-h-screen w-full bg-ivory">
                <StyleContextProvider initialContext={StyleContextKey.Search}>
                    <Navbar currentUser={session.profile} />
                    <UserDetailHeader profile={profile} />
                </StyleContextProvider>
                <FooterComponent />
            </main>
        );
    }
}
