"use server";

import { auth } from "@/auth";
import { StyleContextProvider } from "@/contexts/StyleProvider";
import { StyleContextKey } from "@/objects/enum";
import Navbar from "@/ui/components/navbar";
import UserDetailHeader from "@/ui/pages/entity/user/header";
import FooterComponent from "@/ui/pages/home/footer";
import { getUserProfileData } from "@/lib/data/profile/getUserProfileData";

export default async function ProfilePage() {
    const [session] = await Promise.all([auth()]);

    if (!session) {
        return <div>You shouldn't be here.</div>;
    } else {
        const profile = await getUserProfileData(session.profile?.userid);

        return (
            <main className="min-h-screen w-full bg-coconut-cream">
                <StyleContextProvider initialContext={StyleContextKey.Search}>
                    <Navbar currentUser={session.profile} />
                    <UserDetailHeader profile={profile} />
                </StyleContextProvider>
                <FooterComponent />
            </main>
        );
    }
}
