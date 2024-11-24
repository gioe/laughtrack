"use client";

import { useState, useEffect, useContext, createContext } from "react";
import { TagDataDTO } from "../objects/interface/tag.interface";
import axios from "axios";
import { EntityType } from "../objects/enum";

interface TagList {
    tags: TagDataDTO[];
}
const defaultList: TagList = {
    tags: [],
};

const TagContext = createContext<TagList>(defaultList);

export function TagListProvider({
    type,
    children,
}: {
    type: EntityType;
    children: React.ReactNode;
}) {
    const [tags, setTags] = useState(defaultList);

    const getAffiliates = async () => {
        axios
            .post(`/api/tag`, {
                type: `${type.valueOf()}`,
            })
            .then((response) => {
                console.log(response);
                return response.data;
            })
            .then((data) => {
                if (data) {
                    setTags(data);
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
