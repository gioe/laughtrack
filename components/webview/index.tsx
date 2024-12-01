"use client";

import Iframe from "react-iframe";

interface WebViewProps {
    url: string;
}
const WebView = ({ url }: WebViewProps) => {
    return (
        <div className="object-fill">
            <Iframe
                url={url}
                width="900px"
                height="640px"
                id=""
                className=""
                display="block"
                position="relative"
            />
        </div>
    );
};

export default WebView;
