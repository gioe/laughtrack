import React from "react";

interface GenericTableInterface<T> {
    data: T[];
    keyExtractor: (item: T) => string;
    renderItem: (item: T) => React.ReactNode;
    defaultNode: React.ReactNode;
}

export default function GenericTable<T extends object>({
    data,
    keyExtractor,
    renderItem,
    defaultNode,
}: GenericTableInterface<T>) {
    return (
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
    );
}
