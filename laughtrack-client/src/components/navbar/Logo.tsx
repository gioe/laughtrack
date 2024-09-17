'use client';

import Image from "next/image";

interface LogoProps {
    onClick: () => void;
}

const Logo: React.FC<LogoProps> = ({onClick}) => {
    return (
        <Image alt="Logo" 
        onClick={onClick}
        src="/images/logo.png" 
        layout="fill"
        objectFit="contain"
        objectPosition="left"
        />
    )
}

export default Logo;