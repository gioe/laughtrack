import { getInitials } from "@/util/comedian/getInitials";

type FallbackVariant = "grid" | "lineup" | "hero";

interface ComedianAvatarFallbackProps {
    name: string;
    variant?: FallbackVariant;
    className?: string;
}

const shapeClass: Record<FallbackVariant, string> = {
    grid: "rounded-full",
    lineup: "rounded-xl",
    hero: "rounded-xl",
};

const ComedianAvatarFallback = ({
    name,
    variant = "grid",
    className = "",
}: ComedianAvatarFallbackProps) => {
    const initials = getInitials(name);

    return (
        <div
            role="img"
            aria-label={name}
            style={{
                // Spotlit-from-above vignette over warm near-black — matches the
                // show-card stage treatment rather than the old flat brown chip.
                backgroundImage:
                    "radial-gradient(ellipse 82% 56% at 50% 0%, rgba(247,231,206,0.22), transparent 56%), linear-gradient(180deg, #2a1d14 0%, #120c08 100%)",
            }}
            className={`w-full h-full overflow-hidden ring-1 ring-inset ring-copper/20 ${shapeClass[variant]} ${className}`}
        >
            <svg
                viewBox="0 0 100 100"
                xmlns="http://www.w3.org/2000/svg"
                preserveAspectRatio="xMidYMid slice"
                className="block w-full h-full"
                aria-hidden="true"
            >
                <g fill="#ffffff" fillOpacity="0.08">
                    <circle cx="50" cy="38" r="15" />
                    <ellipse cx="50" cy="86" rx="28" ry="22" />
                </g>
                {initials && (
                    <text
                        x="50"
                        y="54"
                        textAnchor="middle"
                        dominantBaseline="middle"
                        fontFamily='"Gilroy-Bold", "DM Sans", -apple-system, BlinkMacSystemFont, sans-serif'
                        fontWeight="700"
                        fontSize={initials.length === 1 ? 46 : 38}
                        fill="#FAF6E0"
                        letterSpacing="1"
                    >
                        {initials}
                    </text>
                )}
            </svg>
        </div>
    );
};

export default ComedianAvatarFallback;
