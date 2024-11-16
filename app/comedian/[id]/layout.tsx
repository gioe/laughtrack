import EntityBanner from "../../../components/banner";
import EditSocialDataModal from "../../../components/modals/editSocialData";
import MergeComediansModal from "../../../components/modals/merge";
import TagEntityModal from "../../../components/modals/tag";
import { EntityType } from "../../../objects/enum";

export default function Layout({ children }) {
    return (
        <>
            <main>
                <section>
                    <MergeComediansModal entityString={""} />
                    <EditSocialDataModal entityString={""} />
                    <TagEntityModal
                        type={EntityType.Comedian}
                        entityId={1}
                        tagsString={""}
                    />
                </section>
                <section>
                    <EntityBanner entityString={""} />
                </section>
                {children}
            </main>
        </>
    );
}
