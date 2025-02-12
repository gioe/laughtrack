import { auth } from "@/auth";
import { StyleContextProvider } from "@/contexts/StyleProvider";
import { StyleContextKey } from "@/objects/enum";
import { Suspense } from "react";

export default async function EntityDetailLayout({
    children,
}: {
    children: React.ReactNode;
    props: any;
}) {
    const session = await auth();

    return (
        <StyleContextProvider initialContext={StyleContextKey.Search}>
            <Suspense>{children}</Suspense>
        </StyleContextProvider>
    );
}
