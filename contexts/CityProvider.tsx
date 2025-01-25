"use client";

import { CityDTO } from "@/lib/data/cities/getCities";
import { useState, useContext, createContext } from "react";

export interface CityList {
    cities: CityDTO[];
}

interface CityContextType {
    cities: CityDTO[];
}

const defaultList: CityContextType = {
    cities: [],
};

// Export the context
export const CityContext = createContext<CityContextType>(defaultList);

export function CityProvider({
    children,
    initialCities,
}: {
    children: React.ReactNode;
    initialCities: CityDTO[];
}) {
    const [cities, setCityList] = useState<CityDTO[]>(initialCities);
    const contextValue: CityContextType = {
        cities,
    };

    return (
        <CityContext.Provider value={contextValue}>
            {children}
        </CityContext.Provider>
    );
}

export function useCityContext() {
    const context = useContext(CityContext);
    if (!context) {
        throw new Error("useCityContext must be used within a CityProvider");
    }
    return context;
}
