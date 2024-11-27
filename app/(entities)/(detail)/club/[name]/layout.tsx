import EntityBanner from "../../../../../components/banner";
import ClearShowsModal from "../../../../../components/modals/clearClub";
import ScrapeEntityModal from "../../../../../components/modals/scrape";
import TagEntityModal from "../../../../../components/modals/tagEntity";
import { PageEntityContextProvider } from "../../../../../contexts/EntityContext";
import { EntityDataProvider } from "../../../../../contexts/EntityDataContext";

export default async function EntityDetailLayout({
    children,
    params,
}: {
    children: React.ReactNode;
    params: Promise<{ name: string }>;
}) {
    const identifier = (await params).name;

    return (
        <PageEntityContextProvider>
            <EntityDataProvider>
                <main className="flex-grow pt-5 bg-shark">
                    <section>
                        <ScrapeEntityModal identifier={identifier} />
                        <TagEntityModal identifier={identifier} />
                        <ClearShowsModal identifier={identifier} />
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
