import { EntityPageDataProvider } from "@/contexts/EntityPageDataProvider";
import { PageEntityProvider } from "@/contexts/PageEntityProvider";
import { StyleContextProvider } from "@/contexts/StyleProvider";
import { StyleContextKey } from "@/objects/enum";
import EntityBanner from "@/ui/components/banner";

export default async function EntityDetailLayout({
    children,
    params,
}: {
    children: React.ReactNode;
    params: Promise<{ name: string }>;
}) {
    const identifier = (await params).name;

    return (
        <StyleContextProvider initialContext={StyleContextKey.Search}>
            <PageEntityProvider>
                <EntityPageDataProvider>{children}</EntityPageDataProvider>
            </PageEntityProvider>
        </StyleContextProvider>
    );
}
