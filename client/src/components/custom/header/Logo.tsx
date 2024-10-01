'use client';

import Image from "next/image";

const Logo = () => {
    return (
        <div>
                    <Image
        className="rounded-full"
        height="30"
        width="30"
        alt="Avatar"
        src="/images/logo.png"
        />
        </div>
    )
}

export default Logo;