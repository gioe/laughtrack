import { EntityPageDataProvider } from "../../../contexts/EntityPageDataProvider";
import { PageEntityProvider } from "../../../contexts/PageEntityProvider";

export default function EntityDetailLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <PageEntityProvider>
            <EntityPageDataProvider>{children}</EntityPageDataProvider>
        </PageEntityProvider>
    );
}
