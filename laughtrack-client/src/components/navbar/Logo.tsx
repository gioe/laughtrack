'use client';

import Image from "next/image";

const Logo = () => {
    return (
        <Image alt="Logo" 
        src="/images/logo.png" 
        layout="fill"
        objectFit="contain"
        objectPosition="left"
        />
    )
}

export default Logo;