import * as React from "react";
const YouTubeIcon = (
    props: React.JSX.IntrinsicAttributes & React.SVGProps<SVGSVGElement>,
) => (
    <svg
        xmlns="http://www.w3.org/2000/svg"
        width={26}
        height={26}
        fill="none"
        viewBox="0 0 24 24"
        {...props}
    >
        <path
            strokeLinejoin="round"
            d="M20.595 4.46a2.755 2.755 0 0 1 1.945 1.945C22.998 8.12 23 11.7 23 11.7s0 3.58-.46 5.296a2.755 2.755 0 0 1-1.945 1.945C18.88 19.4 12 19.4 12 19.4s-6.88 0-8.595-.46a2.755 2.755 0 0 1-1.945-1.945C1 15.28 1 11.7 1 11.7s0-3.58.46-5.295A2.755 2.755 0 0 1 3.405 4.46C5.12 4 12 4 12 4s6.88 0 8.595.46Zm-5.082 7.24L9.798 15V8.401l5.715 3.3Z"
            clipRule="evenodd"
        />
    </svg>
);
export default YouTubeIcon;
