"use client";

import { useState } from "react";
import { BasicButton } from "../../../../../../../components/button/basic";
import WebView from "../../../../../../../components/webview";
import { scrape } from "../actions";
import { clear } from "../actions";
import { Club } from "../../../../../../../objects/class/club/Club";

interface EditClubFormProps {
    clubString: string;
}

export default function EditClubPageBody({ clubString }: EditClubFormProps) {
    const [isLoading, setIsLoading] = useState(false);

    const club = JSON.parse(clubString) as Club;
    const scrapeWithId = scrape.bind(null, club.id);
    const clearWithId = clear.bind(null, club.id);

    return (
        <div className="flex w-full flex-row pt-7 justify-center">
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
