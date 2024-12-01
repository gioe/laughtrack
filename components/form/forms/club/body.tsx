/* eslint-disable @typescript-eslint/no-explicit-any */

import WebView from "../../../webview";
import { Club } from "../../../../objects/class/club/Club";

interface EditClubFormBodyProps {
    club: Club;
    isLoading: boolean;
    form: any;
}

export default function EditClubFormBody({ club }: EditClubFormBodyProps) {
    return (
        <div className="flex flex-row gap-2 mt-10">
            <div className="flex flex-col gap-2 mx-4">
                {club.socialData?.website && (
                    <WebView url={club.socialData.website} />
                )}
            </div>
        </div>
    );
}
