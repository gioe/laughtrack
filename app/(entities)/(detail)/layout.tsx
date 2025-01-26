import { SortOptionProvider } from "@/contexts/SortOptionProvider";
import { PageEntityProvider } from "@/contexts/PageEntityProvider";
import { StyleContextProvider } from "@/contexts/StyleProvider";
import { StyleContextKey } from "@/objects/enum";
import { FilterDataProvider } from "@/contexts/FilterDataProvider";
import FilterModal from "@/ui/components/modals/filter";

export default async function EntityDetailLayout({
    children,
}: {
    children: React.ReactNode;
    params: Promise<{ name: string }>;
}) {
    return (
        <StyleContextProvider initialContext={StyleContextKey.Search}>
            <PageEntityProvider>
                <FilterDataProvider>
                    <FilterModal />
                    <SortOptionProvider>{children}</SortOptionProvider>
                </FilterDataProvider>
            </PageEntityProvider>
        </StyleContextProvider>
    );
}
