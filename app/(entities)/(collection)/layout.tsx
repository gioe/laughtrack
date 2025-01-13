import { EntityPageDataProvider } from "@/contexts/EntityPageDataProvider";
import { PageEntityProvider } from "@/contexts/PageEntityProvider";
import { Suspense } from "react";

export default function EntityDetailLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <Suspense>
            <PageEntityProvider>
                <EntityPageDataProvider>{children}</EntityPageDataProvider>
            </PageEntityProvider>
        </Suspense>
    );
}
