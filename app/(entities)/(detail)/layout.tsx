import EntityBanner from "../../../components/banner";
import ClearShowsModal from "../../../components/modals/clearClub";
import ModifyLineupModal from "../../../components/modals/modifyLineup";
import ScrapeEntityModal from "../../../components/modals/scrape";
import EditSocialDataModal from "../../../components/modals/socialData";
import TagEntityModal from "../../../components/modals/tagEntity";
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
                <main className="flex-grow pt-5 bg-shark">
                    <section>
                        <ScrapeEntityModal />
                        <ModifyLineupModal />
                        <TagEntityModal />
                        <ClearShowsModal />
                        <EditSocialDataModal />
                    </section>
                    <section>
                        <EntityBanner />
                    </section>
                    {children}
                </main>
            </EntityDataProvider>
        </EntityContext>
    );
}
