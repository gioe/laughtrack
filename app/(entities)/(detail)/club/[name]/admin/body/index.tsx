"use client";

import { useState } from "react";
import { BasicButton } from "../../../../../../../components/button/basic";
import WebView from "../../../../../../../components/webview";
import { clear } from "../actions";
import { Club } from "../../../../../../../objects/class/club/Club";
import { useRouter } from "next/navigation";

interface EditClubFormProps {
    clubString: string;
}

export default function EditClubPageBody({ clubString }: EditClubFormProps) {
    const router = useRouter();
    const [isLoading, setIsLoading] = useState(false);

    const club = JSON.parse(clubString) as Club;
    const clearWithId = clear.bind(null, club.id);

    return (
        <div className="flex w-full flex-row pt-7 justify-center">
            <div className="flex flex-col gap-2 mx-4">
                <h1 className="text-white">
                    {`${club.showCount ?? 0} upcoming shows`}
                </h1>
                <BasicButton
                    clickHandle={async () => {
                        setIsLoading(true);
                        await clearWithId();
                        setIsLoading(false);
                        router.refresh();
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
