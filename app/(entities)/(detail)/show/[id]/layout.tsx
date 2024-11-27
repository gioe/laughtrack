import EntityBanner from "../../../../../components/banner";
import ModifyLineupModal from "../../../../../components/modals/modifyLineup";
import ScrapeEntityModal from "../../../../../components/modals/scrape";
import TagEntityModal from "../../../../../components/modals/tagEntity";
import { PageEntityContextProvider } from "../../../../../contexts/EntityContext";
import { EntityDataProvider } from "../../../../../contexts/EntityDataContext";

export default async function EntityDetailLayout({
    children,
    params,
}: {
    children: React.ReactNode;
    params: Promise<{ id: string }>;
}) {
    const identifier = (await params).id;

    return (
        <PageEntityContextProvider>
            <EntityDataProvider>
                <main className="flex-grow pt-5 bg-shark">
                    <section>
                        <ScrapeEntityModal identifier={identifier} />
                        <ModifyLineupModal identifier={identifier} />
                        <TagEntityModal identifier={identifier} />
                    </section>
                    <section>
                        <EntityBanner identifier={identifier} />
                    </section>
                    {children}
                </main>
            </EntityDataProvider>
        </PageEntityContextProvider>
    );
}
