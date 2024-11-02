import FilterPageContainer from "../../../components/custom/filters/FilterPageContainer";
import EditSocialDataModal from "../../../components/custom/modals/EditSocialDataModal";
import MergeComediansModal from "../../../components/custom/modals/MergeComediansModal";
import EntityBanner from "../../../components/custom/banner/EntityBanner";
import ShowTable from "../../../components/custom/tables/ShowTable";
import useSocialDataModal from "../../../hooks/useSocialDataModal";
import useMergeComediansModal from "../../../hooks/useMergeComediansModal";
import useAddComedianTagModal from "../../../hooks/useAddComedianTagModal";
import TagEntityModal from "../../../components/custom/modals/TagEntityModal";
import { EntityType } from "../../../util/enum";
import { SearchParams } from "../../../interfaces/searchParams.interface";
import { db } from "../../../database";
import { Suspense } from "react";
import { TagInterface } from "../../../interfaces/tag.interface";
import { SORT_OPTIONS } from "../../../util/sort";
import { ComedianInterface } from "../../../interfaces/comedian.interface";
import { Paginated } from "../../../interfaces/paginated.interface";

const menuItems = [
    { key: "social", label: "Edit Social Data", store: useSocialDataModal },
    { key: "merge", label: "Merge Comedians", store: useMergeComediansModal },
    { key: "tags", label: "Add Tags", store: useAddComedianTagModal },
];

interface ComedianDetailPageInterface extends Paginated {
    comedian: ComedianInterface | null;
    tags: TagInterface[];
}

async function getComedianDetail(
    id: string,
    params: SearchParams,
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

    const { totalResults, comedian, tags } = await getComedianDetail(
        params.id,
        searchParams,
    );

    return (
        <div className="flex flex-col">
            {comedian && (
                <div>
                    <MergeComediansModal comedian={comedian} />
                    <EditSocialDataModal comedian={comedian} />
                    <TagEntityModal
                        entity={comedian}
                        type={EntityType.Comedian}
                        tags={tags}
                    />
                </div>
            )}

            <section>
                {comedian && (
                    <EntityBanner entity={comedian} menuItems={menuItems} />
                )}
            </section>
            <section>
                <FilterPageContainer
                    itemCount={totalResults}
                    sortOptions={SORT_OPTIONS.SHOW}
                    child={
                        <Suspense
                            key={
                                (searchParams?.query ?? 1) +
                                (searchParams?.page ?? "")
                            }
                            fallback={<div />}
                        >
                            <ShowTable params={searchParams} />
                        </Suspense>
                    }
                />
            </section>
        </div>
    );
}
