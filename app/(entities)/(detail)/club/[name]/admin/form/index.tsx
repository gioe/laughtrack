"use client";

import { useState } from "react";
import {
    clear,
    scrape,
} from "../../../../app/(entities)/(detail)/club/admin/[name]/actions";
import { Club } from "../../../../objects/class/club/Club";
import { BasicButton } from "../../../button/basic";
import WebView from "../../../webview";

interface EditClubFormProps {
    clubString: string;
}

export default function EditClubForm({ clubString }: EditClubFormProps) {
    const [isLoading, setIsLoading] = useState(false);

    const club = JSON.parse(clubString) as Club;
    const scrapeWithId = scrape.bind(null, club.id);
    const clearWithId = clear.bind(null, club.id);

    return (
        <div className="flex flex-row gap-2 pt-10 pb-10">
            <div className="flex flex-col gap-2 mx-4">
                <BasicButton
                    clickHandle={async () => {
                        setIsLoading(true);
                        await scrapeWithId();
                        setIsLoading(false);
                    }}
                    text="Scrape"
                    isLoading={isLoading}
                />
                <BasicButton
                    clickHandle={async () => {
                        setIsLoading(true);
                        await clearWithId();
                        setIsLoading(false);
                    }}
                    text="Clear"
                    isLoading={isLoading}
                />
            </div>
            <div className="flex flex-col gap-2 mx-4">
                {club.socialData?.website && (
                    <WebView url={club.socialData.website} />
                )}
            </div>
        </div>
    );
}
