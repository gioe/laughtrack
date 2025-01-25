import { SortOptionProvider } from "@/contexts/SortOptionProvider";
import { PageEntityProvider } from "@/contexts/PageEntityProvider";
import { StyleContextProvider } from "@/contexts/StyleProvider";
import { StyleContextKey } from "@/objects/enum";
import { Suspense } from "react";
import { FilterDataProvider } from "@/contexts/FilterDataProvider";
import FilterModal from "@/ui/components/modals/filter";

export default function EntityDetailLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <StyleContextProvider initialContext={StyleContextKey.Search}>
            <Suspense>
                <PageEntityProvider>
                    <FilterDataProvider>
                        <FilterModal />
                        <SortOptionProvider>{children}</SortOptionProvider>
                    </FilterDataProvider>
                </PageEntityProvider>
            </Suspense>
        </StyleContextProvider>
    );
}
