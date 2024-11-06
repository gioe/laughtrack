import React, { Suspense } from "react";

interface GenericTableInterface<T> {
    data: T[];
    keyExtractor: (item: T) => string;
    renderItem: (item: T) => React.ReactNode;
    defaultNode: React.ReactNode;
    suspenseKey: string;
}

export default async function GenericTable<T extends object>({
    data,
    suspenseKey,
    keyExtractor,
    renderItem,
    defaultNode,
}: GenericTableInterface<T>) {
    return (
        <Suspense key={suspenseKey} fallback={<div />}>
            <main className="flex flex-col">
                <section className="flex-grow flex-row">
                    <div className="flex flex-col">
                        {data.length > 0 ? (
                            data.map((item) => {
                                return (
                                    <div key={keyExtractor(item)}>
                                        {renderItem(item)}
                                    </div>
                                );
                            })
                        ) : (
                            <div>{defaultNode}</div>
                        )}
                    </div>
                </section>
            </main>
        </Suspense>
    );
}
