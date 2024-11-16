import EntityBanner from "../../../components/banner";
import ClearShowsModal from "../../../components/modals/clear";
import ScrapeEntityModal from "../../../components/modals/scrape";
import { EntityType } from "../../../objects/enum";

export default function Layout({ children }) {
    return (
        <>
            <main>
                <section>
                    <ScrapeEntityModal entityId={1} type={EntityType.Club} />
                    <ClearShowsModal clubId={1} />
                </section>
                <section>
                    <EntityBanner entityString={""} />
                </section>
                {children}
            </main>
        </>
    );
}
