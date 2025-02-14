"use client";

import { createContext, useContext, ReactNode, useState } from "react";

const ParamsContext = createContext({
    searchParams: "",
    updateParams: (params: string) => {},
});

interface ParamsProviderProps {
    children: ReactNode;
    value: "";
}

export function ParamsProvider({ children, value }: ParamsProviderProps) {
    const [searchParams, setSearchParams] = useState<string>(value);

    const updateParams = (value: string) => {
        setSearchParams(value);
    };

    return (
        <ParamsContext.Provider value={{ searchParams, updateParams }}>
            {children}
        </ParamsContext.Provider>
    );
}

export function useParams() {
    const context = useContext(ParamsContext);
    if (context === undefined) {
        throw new Error("useParams must be used within a ParamsProvider");
    }
    return context;
}
