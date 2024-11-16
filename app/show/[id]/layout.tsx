import EntityBanner from "../../../components/banner";
import ModifyLineupModal from "../../../components/modals/modifyLineup";
import ScrapeEntityModal from "../../../components/modals/scrape";
import TagEntityModal from "../../../components/modals/tag";
import { EntityType } from "../../../objects/enum";

export default function Layout({ children }) {
    return (
        <>
            <main>
                <ScrapeEntityModal entityId={1} type={EntityType.Show} />
                <ModifyLineupModal entityString={""} />
                <TagEntityModal
                    type={EntityType.Show}
                    entityId={1}
                    tagsString={""}
                />
                <section>
                    <EntityBanner entityString={""} />
                </section>
                {children}
            </main>
        </>
    );
}
