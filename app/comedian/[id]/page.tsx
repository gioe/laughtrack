import EntityBanner from "../../../components/banner";
import TagEntityModal from "../../../components/modals/tagEntity";
import { EntityType } from "../../../util/enum";
import { SearchParams } from "../../../objects/interfaces/searchParams.interface";
import { getDB } from "../../../database";
import { TagInterface } from "../../../objects/interfaces/tag.interface";
import { Comedian } from "../../../objects/classes/comedian/Comedian";
import { getSortOptionsForEntityType } from "../../../util/sort";
import QueryableTableContainer from "../../../components/container";
import MergeComediansModal from "../../../components/modals/comedian/merge";
import EditSocialDataModal from "../../../components/modals/comedian/editSocialData";

const { db } = getDB();

interface ComedianDetailPageInterface {
    comedian: Comedian | null;
    tags: TagInterface[];
}

async function getComedianDetail(
    id: string,
    searchParams: SearchParams,
): Promise<ComedianDetailPageInterface> {
    const comedian = db.comedians.getById(Number(id), searchParams);
    const tags = db.tags.getByType(EntityType.Comedian.valueOf());

    return Promise.all([comedian, tags]).then((responses) => {
        const comedian = responses[0];
        const tags = responses[1];
        return {
            comedian,
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

    const { comedian, tags } = await getComedianDetail(params.id, searchParams);
    const comedianString = JSON.stringify(comedian);
    const tagsString = JSON.stringify(tags);
    const sortOptions = getSortOptionsForEntityType(EntityType.Show);

    return (
        <div className="flex flex-col">
            {comedian && (
                <div>
                    <MergeComediansModal comedianString={comedianString} />
                    <EditSocialDataModal comedianString={comedianString} />
                    <TagEntityModal
                        type={EntityType.Comedian}
                        entityId={comedian.id}
                        tagsString={tagsString}
                    />
                </div>
            )}

            <section>
                {comedian && <EntityBanner entityString={comedianString} />}
            </section>
            <section>
                <QueryableTableContainer
                    sortOptions={sortOptions}
                    resultString={JSON.stringify(comedian?.dates)}
                    defaultNode={<div></div>}
                />
            </section>
        </div>
    );
}
