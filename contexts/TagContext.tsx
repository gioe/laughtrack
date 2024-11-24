import { useState, useEffect, useContext, createContext } from "react";
import { TagDataDTO } from "../objects/interface/tag.interface";
import axios from "axios";

interface TagList {
    tags: TagDataDTO[];
}
const defaultList: TagList = {
    tags: [],
};

const TagContext = createContext<TagList>(defaultList);

export function TagListProvider({ children }: { children: React.ReactNode }) {
    const [state, setState] = useState(defaultList);

    const getAffiliates = async () => {
        axios
            .post(`/api/tag`, {
                type: "show",
            })
            .then((response) => response.data)
            .then((data) => {
                if (data) {
                    console.log(data);
                }
            })
            .catch((error: Error) => {
                console.log(error);
            });
    };

    useEffect(() => {
        getAffiliates();
    }, []);

    return <TagContext.Provider value={state}>{children}</TagContext.Provider>;
}

export function useTagContext() {
    return useContext(TagContext);
}
