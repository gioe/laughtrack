import { PageEntityProvider } from "@/contexts/PageEntityProvider";
import { StyleContextProvider } from "@/contexts/StyleProvider";
import { StyleContextKey } from "@/objects/enum";
import { Suspense } from "react";

export default function EntityDetailLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <StyleContextProvider initialContext={StyleContextKey.Search}>
            <Suspense>
                <PageEntityProvider>{children}</PageEntityProvider>
            </Suspense>
        </StyleContextProvider>
    );
}
