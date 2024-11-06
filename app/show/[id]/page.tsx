import { getDB } from "../../../database";
import { TagInterface } from "../../../objects/interfaces/tag.interface";
import { SearchParams } from "../../../objects/interfaces/searchParams.interface";
import { EntityType } from "../../../util/enum";
import EntityBanner from "../../../components/custom/banner/EntityBanner";
import AddComedianModal from "../../../components/custom/modals/AddComedianModal";
import TagEntityModal from "../../../components/custom/modals/TagEntityModal";
import FilterPageContainer from "../../../components/custom/filters/FilterPageContainer";
import { Show } from "../../../objects/classes/show/Show";
import { Comedian } from "../../../objects/classes/comedian/Comedian";
import BasicEntityCard from "../../../components/custom/tables/cards/BasicEntityCard";

const { db } = getDB();

interface ShowDetailPageInterface {
    show: Show | null;
    tags: TagInterface[];
}

async function getShowDetail(id: string): Promise<ShowDetailPageInterface> {
    const show = db.shows.getById(Number(id));
    const tags = db.tags.getByType(EntityType.Show.valueOf());

    return Promise.all([show, tags]).then((responses) => {
        return {
            show: responses[0],
            tags: responses[1],
        };
    });
}

export default async function ShowDetailPage(props: {
    params: Promise<{ id: string }>;
    searchParams: Promise<SearchParams>;
}) {
    const searchParams = await props.searchParams;
    const params = await props.params;

    const { show, tags } = await getShowDetail(params.id);

    return (
        <div>
            {show && (
                <main className="flex-grow pt-5 bg-shark">
                    <AddComedianModal show={show} intialComedians={[]} />
                    <TagEntityModal entity={show} tags={tags} />
                    <section>
                        <EntityBanner entity={show} />
                    </section>
                    <section>
                        <FilterPageContainer<Comedian>
                            suspenseKey={
                                (searchParams.query ?? "") +
                                (searchParams.page ?? 0)
                            }
                            renderItem={(entity) => {
                                return <BasicEntityCard entity={entity} />;
                            }}
                            results={show.lineup}
                            defaultNode={<div></div>}
                        />
                    </section>
                </main>
            )}
        </div>
    );
}
