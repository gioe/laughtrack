import { PageEntityContextProvider } from "../../../contexts/EntityContext";
import { EntityDataProvider } from "../../../contexts/EntityDataContext";

export default function EntityDetailLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <PageEntityContextProvider>
            <EntityDataProvider>{children}</EntityDataProvider>
        </PageEntityContextProvider>
    );
}
