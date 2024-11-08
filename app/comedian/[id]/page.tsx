import FilterPageContainer from "../../../components/custom/filters/FilterPageContainer";
import EditSocialDataModal from "../../../components/custom/modals/EditSocialDataModal";
import MergeComediansModal from "../../../components/custom/modals/MergeComediansModal";
import EntityBanner from "../../../components/custom/banner/EntityBanner";
import TagEntityModal from "../../../components/custom/modals/TagEntityModal";
import { EntityType } from "../../../util/enum";
import { SearchParams } from "../../../objects/interfaces/searchParams.interface";
import { getDB } from "../../../database";
import { TagInterface } from "../../../objects/interfaces/tag.interface";
import { Comedian } from "../../../objects/classes/comedian/Comedian";

const { db } = getDB();

interface ComedianDetailPageInterface {
    comedian: Comedian | null;
    tags: TagInterface[];
}

async function getComedianDetail(
    id: string,
): Promise<ComedianDetailPageInterface> {
    const comedian = db.comedians.getByName(id);
    const tags = db.tags.getByType(EntityType.Comedian.valueOf());

    return Promise.all([comedian, tags]).then((responses) => {
        const comedian = responses[0];
        const tags = responses[1];
        return {
            comedian,
            totalResults: comedian?.dates.length ?? 0,
            tags,
        };
    });
}

export default async function ComedianDetailsPage(props: {
    params: Promise<{ id: string }>;
    searchParams: Promise<SearchParams>;
}) {
    const searchParams = await props.searchParams;
    const params = await props.params;

    const { comedian, tags } = await getComedianDetail(params.id);

    return (
        <div className="flex flex-col">
            {comedian && (
                <div>
                    <MergeComediansModal comedian={comedian} />
                    <EditSocialDataModal comedian={comedian} />
                    <TagEntityModal entity={comedian} tags={tags} />
                </div>
            )}

            <section>{comedian && <EntityBanner entity={comedian} />}</section>
            <section>
                <FilterPageContainer
                    resultString={JSON.stringify([])}
                    defaultNode={<div></div>}
                />
            </section>
        </div>
    );
}
