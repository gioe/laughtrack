"use client";

import { useState, useContext, createContext } from "react";
import { EntityType } from "../objects/enum";
import { usePathname } from "next/navigation";

interface PageEntityContext {
    primaryEntity: EntityType | undefined;
    secondaryEntity: EntityType | undefined;
}

const defaultState: PageEntityContext = {
    primaryEntity: undefined,
    secondaryEntity: undefined,
};

const PageEntityContext = createContext<PageEntityContext>(defaultState);

export function PageEntityProvider({
    children,
}: {
    children: React.ReactNode;
}) {
    const pathName = usePathname();

    const [state /* setEntityType */] = useState(getStateFromPath(pathName));

    return (
        <PageEntityContext.Provider value={state}>
            {children}
        </PageEntityContext.Provider>
    );
}

const getStateFromPath = (path: string): PageEntityContext => {
    let primaryEntity: EntityType | undefined;
    let secondaryEntity: EntityType | undefined;

    if (path.startsWith("/club")) {
        primaryEntity = EntityType.Club;
        secondaryEntity = path.includes("/all")
            ? EntityType.Club
            : EntityType.Show;
    } else if (path.startsWith("/show")) {
        primaryEntity = EntityType.Show;
        secondaryEntity = path.includes("/all")
            ? EntityType.Show
            : EntityType.Comedian;
    } else if (path.startsWith("/comedian")) {
        primaryEntity = EntityType.Comedian;
        secondaryEntity = path.includes("/all")
            ? EntityType.Comedian
            : EntityType.Show;
    }

    return {
        primaryEntity,
        secondaryEntity,
    };
};

export function usePageContext() {
    return useContext(PageEntityContext);
}
