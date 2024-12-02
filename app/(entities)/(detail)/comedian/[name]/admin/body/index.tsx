import WebView from "../../../../../../../components/webview";
import { Comedian } from "../../../../../../../objects/class/comedian/Comedian";
import EditComedianForm from "./form";

interface EditComedianPageBodyProps {
    comedianString: string;
}

export default function EditComedianPageBody({
    comedianString,
}: EditComedianPageBodyProps) {
    const comedian = JSON.parse(comedianString) as Comedian;

    return (
        <div className="flex w-full flex-row pt-7 justify-center">
            <div>
                <EditComedianForm comedian={comedian} />
            </div>
            <div>
                {comedian.socialData?.website && (
                    <WebView url={comedian.socialData?.website} />
                )}
            </div>
        </div>
    );
}
