import { EntityPageDataProvider } from "@/contexts/EntityPageDataProvider";
import { PageEntityProvider } from "@/contexts/PageEntityProvider";
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
        <PageEntityProvider>
            <EntityPageDataProvider>{children}</EntityPageDataProvider>
        </PageEntityProvider>
    );
}
