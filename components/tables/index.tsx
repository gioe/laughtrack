import React from "react";

interface TableProps<T> {
    data: T[];
    keyExtractor: (item: T) => string;
    renderItem: (item: T) => React.ReactNode;
    defaultNode: React.ReactNode;
}

export default function Table<T extends object>({
    data,
    keyExtractor,
    renderItem,
    defaultNode,
}: TableProps<T>) {
    return (
        <main className={"grid grid-cols-1 gap-4"}>
            {data.length > 0 ? (
                data.map((item) => {
                    return (
                        <div key={keyExtractor(item)}>{renderItem(item)}</div>
                    );
                })
            ) : (
                <div>{defaultNode}</div>
            )}
            a
        </main>
    );
}
