import { EntityContext } from "../../../contexts/EntityContext";
import { EntityDataProvider } from "../../../contexts/EntityDataContext";

export default function EntityDetailLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <EntityContext>
            <EntityDataProvider>
                <main className="flex-grow pt-5 bg-shark">{children}</main>
            </EntityDataProvider>
        </EntityContext>
    );
}
