import type { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import type { ComedianLineupDTO } from "@/objects/class/comedian/comedianLineup.interface";
import type { ShowDTO } from "@/objects/class/show/show.interface";

export function mapComedianDtoToV1Wire(comedian: ComedianDTO): object {
    const {
        socialData,
        showCount,
        coAppearances,
        dates,
        parentComedian,
        ...rest
    } = comedian;

    return {
        ...rest,
        social_data: socialData,
        show_count: showCount,
        ...(coAppearances !== undefined
            ? { co_appearances: coAppearances }
            : {}),
        ...(dates !== undefined
            ? { dates: dates.map(mapShowDtoToV1Wire) }
            : {}),
        ...(parentComedian !== undefined
            ? { parentComedian: mapComedianDtoToV1Wire(parentComedian) }
            : {}),
    };
}

export function mapComedianLineupDtoToV1Wire(
    comedian: ComedianLineupDTO,
): object {
    const { socialData, showCount, parentComedian, lineupItems, ...rest } =
        comedian;

    return {
        ...rest,
        ...(socialData !== undefined ? { social_data: socialData } : {}),
        ...(showCount !== undefined ? { show_count: showCount } : {}),
        ...(parentComedian !== undefined
            ? { parentComedian: mapComedianLineupDtoToV1Wire(parentComedian) }
            : {}),
        ...(lineupItems !== undefined
            ? {
                  lineupItems: lineupItems.map((item) => ({
                      ...item,
                      comedian: mapComedianLineupDtoToV1Wire(item.comedian),
                  })),
              }
            : {}),
    };
}

export function mapShowDtoToV1Wire(show: ShowDTO): object {
    const { clubId, socialData, lineup, ...rest } = show;

    return {
        ...rest,
        clubID: clubId,
        ...(socialData !== undefined ? { social_data: socialData } : {}),
        ...(lineup !== undefined
            ? { lineup: lineup.map(mapComedianLineupDtoToV1Wire) }
            : {}),
    };
}
