"use client";
import Logo from "../logo";
import NavigationMenu from "../navbar/menu";
import AuthButtons from "../auth/header";
import { useCallback } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { UserProfileInterface } from "@/app/api/profile/[id]/interface";
import { useStyleContext } from "@/contexts/StyleProvider";
import { useLoginModal } from "@/hooks";
import { useSignOut } from "@/hooks/useSignOut";
import { FullRoundedButton } from "../button/rounded/full";

interface HeaderProps {
    currentUser?: UserProfileInterface | null;
}

const MOBILE_NAV_ITEMS = [
    { title: "Shows", href: "/show/search", match: "/show" },
    { title: "Clubs", href: "/club/search", match: "/club" },
    { title: "Comedians", href: "/comedian/search", match: "/comedian" },
];

function MobileNavLink({
    title,
    href,
    highlighted,
    baseColor,
    highlightedColor,
}: {
    title: string;
    href: string;
    highlighted: boolean;
    baseColor: string;
    highlightedColor: string;
}) {
    return (
        <Link
            href={href}
            aria-current={highlighted ? "page" : undefined}
            className={`flex-1 text-center text-[15px] font-semibold font-dmSans py-2 rounded-lg transition-all duration-200 ${
                highlighted
                    ? `${highlightedColor} bg-copper/20`
                    : `${baseColor} opacity-70 hover:opacity-100 hover:bg-copper/10`
            }`}
        >
            {title}
        </Link>
    );
}

export function Header({ currentUser }: HeaderProps) {
    const { getCurrentStyles } = useStyleContext();
    const styleConfig = getCurrentStyles();
    const pathname = usePathname();

    const loginModal = useLoginModal();
    const handleSignOut = useSignOut();

    const handleLoginClick = useCallback(() => {
        loginModal.onOpen();
    }, [loginModal]);

    return (
        <header
            className={`relative px-4 py-4 ${styleConfig.headerBackgroundColor}`}
        >
            <nav aria-label="Main navigation">
                <div className="lg:hidden">
                    <div className="flex items-center justify-between">
                        <Link href="/" aria-label="Laughtrack home">
                            <Image
                                src="/logomark.svg"
                                alt="Laughtrack"
                                width={32}
                                height={32}
                                className="shrink-0"
                            />
                        </Link>
                        {currentUser ? (
                            <div className="flex items-center gap-4">
                                <Link
                                    href={`/profile/${currentUser.id}`}
                                    aria-current={
                                        pathname.includes("/profile")
                                            ? "page"
                                            : undefined
                                    }
                                    className={`text-[15px] font-semibold font-dmSans transition-opacity ${
                                        styleConfig.baseHeaderItemColor
                                    } ${
                                        pathname.includes("/profile")
                                            ? "opacity-100"
                                            : "opacity-70 hover:opacity-100"
                                    }`}
                                >
                                    Profile
                                </Link>
                                <button
                                    type="button"
                                    onClick={handleSignOut}
                                    className={`text-[15px] font-semibold font-dmSans opacity-70 hover:opacity-100 transition-opacity ${styleConfig.baseHeaderItemColor}`}
                                >
                                    Log Out
                                </button>
                            </div>
                        ) : (
                            <FullRoundedButton
                                handleClick={handleLoginClick}
                                label="Log In"
                            />
                        )}
                    </div>
                    <div className="mt-3 flex items-center gap-1 border-t border-copper/30 pt-2">
                        {MOBILE_NAV_ITEMS.map((item) => (
                            <MobileNavLink
                                key={item.title}
                                title={item.title}
                                href={item.href}
                                highlighted={pathname.includes(item.match)}
                                baseColor={styleConfig.baseHeaderItemColor}
                                highlightedColor={
                                    styleConfig.headerItemColorHighlighted
                                }
                            />
                        ))}
                    </div>
                </div>
                <div className="hidden max-w-7xl mx-auto items-center lg:grid lg:grid-cols-3 ">
                    <div className="col-start-1">
                        <Logo />
                    </div>
                    <div className="col-start-2 justify-self-center">
                        <NavigationMenu pathname={pathname} />
                    </div>
                    <div className="col-start-3 justify-self-end">
                        <AuthButtons
                            currentUser={currentUser}
                            pathname={pathname}
                            onLogin={handleLoginClick}
                        />
                    </div>
                </div>
            </nav>
        </header>
    );
}
