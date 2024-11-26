"use client";

import { useState, useContext, createContext } from "react";
import { EntityType } from "../objects/enum";
import { usePathname } from "next/navigation";

interface EntityTypeContext {
    currentEntityContext: EntityType | undefined;
}

const defaultState: EntityTypeContext = {
    currentEntityContext: undefined,
};

const EntityTypeContext = createContext<EntityTypeContext>(defaultState);

export function EntityContext({ children }: { children: React.ReactNode }) {
    const pathName = usePathname();

    const [state /* setEntityType */] = useState({
        currentEntityContext: getTypeFromPath(pathName),
    });

    return (
        <EntityTypeContext.Provider value={state}>
            {children}
        </EntityTypeContext.Provider>
    );
}

const getTypeFromPath = (path: string): EntityType | undefined => {
    if (path.startsWith("/club")) {
        return EntityType.Club;
    } else if (path.startsWith("/show")) {
        return EntityType.Show;
    } else if (path.startsWith("/comedian")) {
        return EntityType.Comedian;
    } else {
        return undefined;
    }
};

export function useEntityTypeContext() {
    return useContext(EntityTypeContext);
}
