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
        // No user so no access to profile
    }

    if (session?.user.id !== params.id) {
        // Mismatch
    }

    const profile = await getUserProfileData(session!.user.id);

    return (
        <main className="min-h-screen w-full bg-ivory">
            <StyleContextProvider initialContext={StyleContextKey.Search}>
                <Navbar currentUser={session?.user} />
                <UserDetailHeader profile={profile} />
            </StyleContextProvider>
            <FooterComponent />
        </main>
    );
}
