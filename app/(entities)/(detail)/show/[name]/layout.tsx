import EntityBanner from "../../../../../components/banner";
import ModifyLineupModal from "../../../../../components/modals/modifyLineup";
import ScrapeEntityModal from "../../../../../components/modals/scrape";
import TagEntityModal from "../../../../../components/modals/tagEntity";
import { EntityPageDataProvider } from "../../../../../contexts/EntityPageDataProvider";
import { PageEntityProvider } from "../../../../../contexts/PageEntityProvider";

export default async function EntityDetailLayout({
    children,
    params,
}: {
    children: React.ReactNode;
    params: Promise<{ id: string }>;
}) {
    const identifier = (await params).id;

    return (
        <PageEntityProvider>
            <EntityPageDataProvider>
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
            </EntityPageDataProvider>
        </PageEntityProvider>
    );
}
