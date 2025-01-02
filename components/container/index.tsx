"use server";

import { Entity } from "../../objects/interface";
import Table from "../table";
import TableFilterBar from "../filter";

interface QueryableEntityTableContainerProps {
    entityCollectionString: string;
    defaultNode: React.ReactNode;
    totalEntities: number;
    cardRenderFunction: (entity: Entity) => JSX.Element;
}

export default function QueryableEntityTableContainer({
    entityCollectionString,
    defaultNode,
    totalEntities,
    cardRenderFunction,
}: QueryableEntityTableContainerProps) {
    const filteredEntityCollection = JSON.parse(
        entityCollectionString,
    ) as Entity[];

    return (
        <main className="mx-auto px-10 flex-item items-end justify-end">
            <section>
                <TableFilterBar totalItems={totalEntities} />
            </section>
            <section>
                <Table
                    keyExtractor={(item) => item.id.toString()}
                    data={filteredEntityCollection}
                    defaultNode={defaultNode}
                    renderItem={cardRenderFunction}
                />
            </section>
        </main>
    );
}
