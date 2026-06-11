"use client";

import React from "react";
import { Building2, CalendarDays } from "lucide-react";
import { Club } from "@/objects/class/club/Club";
import { ClubDTO } from "@/objects/class/club/club.interface";
import type { SiblingClubDTO } from "@/lib/data/club/detail/findSiblingClubs";
import ClubDataColumn from "../social";
import ChainLocationDropdown, {
    ChainLocation,
} from "@/ui/pages/entity/club/chainLocations";
import { useMotionProps } from "@/hooks";
import { motion } from "framer-motion";
import { stripHtmlTags } from "@/util/primatives/stringUtil";
import MarqueeHero from "@/ui/pages/entity/MarqueeHero";

const PLACEHOLDER = "/placeholders/club-placeholder.svg";

const locationLabelFor = (
    city?: string | null,
    state?: string | null,
): string | null =>
    city && state ? `${city}, ${state}` : city || state || null;

interface ClubDetailHeaderProps {
    club: ClubDTO;
    siblings?: SiblingClubDTO[];
}

const ClubDetailHeader: React.FC<ClubDetailHeaderProps> = ({
    club,
    siblings = [],
}) => {
    const parsedClub = new Club(club);

    // Build the chain location list (current club + siblings) for the switcher.
    const chainLocations: ChainLocation[] =
        club.chainName && siblings.length > 0
            ? [
                  {
                      name: parsedClub.name,
                      locationLabel: locationLabelFor(
                          parsedClub.city,
                          parsedClub.state,
                      ),
                      isCurrent: true,
                  },
                  ...siblings.map((sibling) => ({
                      name: sibling.name,
                      locationLabel: locationLabelFor(
                          sibling.city,
                          sibling.state,
                      ),
                      isCurrent: false,
                  })),
              ].sort((a, b) => a.name.localeCompare(b.name))
            : [];
    const { mv, springs } = useMotionProps();
    const isFestival = parsedClub.clubType === "festival";
    const locationLabel = isFestival
        ? parsedClub.city && parsedClub.state
            ? `${parsedClub.city}, ${parsedClub.state}`
            : parsedClub.city || parsedClub.state || ""
        : parsedClub.city && parsedClub.state
          ? `${parsedClub.city}, ${parsedClub.state}`
          : parsedClub.city || parsedClub.address;

    // Parity with iOS ClubDetailHeroPresentation: fall back to imageUrl when
    // heroUrl is empty so clubs with only a logo still render artwork.
    const isUsableUrl = (url?: string | null) => !!url && url !== PLACEHOLDER;
    const heroSrc = isUsableUrl(parsedClub.heroUrl)
        ? parsedClub.heroUrl
        : isUsableUrl(parsedClub.imageUrl)
          ? parsedClub.imageUrl
          : null;

    return (
        <div className="max-w-7xl mx-auto">
            <MarqueeHero
                title={parsedClub.name}
                eyebrow={locationLabel}
                imageSrc={heroSrc}
                imageAlt={parsedClub.name}
                fallback={
                    <div className="flex h-full w-full items-center justify-center bg-surface-muted">
                        <Building2
                            size={64}
                            className="text-accent-strong"
                            aria-hidden="true"
                        />
                    </div>
                }
            >
                <div className="flex flex-col items-center gap-3">
                    {isFestival && (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-highlight/85 text-foreground text-xs font-semibold uppercase tracking-wide">
                            <CalendarDays className="w-3.5 h-3.5" />
                            Festival
                        </span>
                    )}
                    {club.chainName && (
                        <p className="text-sm text-white/65 italic">
                            Part of the {club.chainName} family
                        </p>
                    )}
                </div>
            </MarqueeHero>

            {chainLocations.length > 1 && club.chainName && (
                <div className="px-6 pt-6">
                    <ChainLocationDropdown
                        chainName={club.chainName}
                        locations={chainLocations}
                    />
                </div>
            )}

            {stripHtmlTags(parsedClub.description) !== "" && (
                <motion.p
                    initial={{ opacity: 0, y: mv(10) }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ ...springs.contentEntrance, delay: mv(0.25) }}
                    className="px-6 pt-6 max-w-3xl font-dmSans text-body leading-relaxed text-foreground whitespace-pre-line"
                >
                    {stripHtmlTags(parsedClub.description)}
                </motion.p>
            )}

            {/* Contact info below hero */}
            <div className="p-6">
                <ClubDataColumn club={club} />
            </div>
        </div>
    );
};

export default ClubDetailHeader;
