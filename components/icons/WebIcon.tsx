import * as React from "react";
const WebIcon = (
    props: React.JSX.IntrinsicAttributes & React.SVGProps<SVGSVGElement>,
) => (
    <svg
        xmlns="http://www.w3.org/2000/svg"
        width={24}
        height={24}
        viewBox="0 0 14 14"
        {...props}
    >
        <g strokeLinecap="round" strokeLinejoin="round">
            <circle cx={7} cy={7} r={6.5} />
            <path d="M.5 7h13m-4 0A11.22 11.22 0 0 1 7 13.5 11.22 11.22 0 0 1 4.5 7 11.22 11.22 0 0 1 7 .5 11.22 11.22 0 0 1 9.5 7Z" />
        </g>
    </svg>
);
export default WebIcon;
