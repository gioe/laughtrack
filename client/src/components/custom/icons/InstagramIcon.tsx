import * as React from "react"
const InstagramIcon = (props: React.JSX.IntrinsicAttributes & React.SVGProps<SVGSVGElement>) => (
  <svg
    className="hover:fill-current"
    xmlns="http://www.w3.org/2000/svg"
    width={30}
    height={30}
    viewBox="0 0 14 14"
    {...props}
  >
    <g
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M10.333 3.644a.25.25 0 1 1 0-.5m0 .5a.25.25 0 1 0 0-.5" />
      <path d="M.858 3.431A2.573 2.573 0 0 1 3.431.858h6.862a2.573 2.573 0 0 1 2.573 2.573v6.862a2.573 2.573 0 0 1-2.573 2.573H3.43a2.573 2.573 0 0 1-2.573-2.573V3.43Z" />
      <path d="M4.312 6.862a2.55 2.55 0 1 0 5.1 0 2.55 2.55 0 1 0-5.1 0" />
    </g>
  </svg>
)
export default InstagramIcon
