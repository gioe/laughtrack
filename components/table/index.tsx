import React from "react";
import { Entity } from "../../objects/interface";
import { cn } from "../../util/tailwindUtil";
import { EntityType } from "../../objects/enum";

interface TableProps<T extends Entity> {
    data: T[];
    keyExtractor: (item: T) => string;
    renderItem: (item: T) => React.ReactNode;
    defaultNode: React.ReactNode;
}

export default function Table<T extends Entity>({
    data,
    keyExtractor,
    renderItem,
    defaultNode,
}: TableProps<T>) {
    const determineLayout = () => {
        const firstObject = data[0];
        if (firstObject !== undefined) {
            switch (data[0].type) {
                case EntityType.Club:
                    return "grid grid-cols-1 gap-4";
                default:
                    return "grid grid-cols-1 gap-x-20 gap-y-10";
            }
        }
        return "grid grid-cols-1 gap-x-20 gap-y-10";
    };

    return (
        <main className={cn(determineLayout())}>
            {data.length > 0 ? (
                data.map((item) => {
                    return (
                        <div className="w-3/4" key={keyExtractor(item)}>
                            {renderItem(item)}
                        </div>
                    );
                })
            ) : (
                <div className="max-w-7xl">{defaultNode}</div>
            )}
        </main>
    );
}
