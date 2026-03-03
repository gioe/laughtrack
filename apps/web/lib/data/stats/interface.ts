/**
 * Represents the statistics data for the platform
 */
export interface StatsDTO {
    /** Number of active clubs in the platform */
    clubCount: number;
    /** Number of upcoming shows in the platform */
    showCount: number;
    /** Number of comedians in the platform */
    comedianCount: number;
}

/**
 * Response wrapper for stats data
 */
export interface StatsDataResponse {
    /** The statistics data */
    stats: StatsDTO;
}

/**
 * Type guard to check if an object is a valid StatsDTO
 */
export function isValidStatsDTO(data: unknown): data is StatsDTO {
    if (typeof data !== 'object' || data === null) return false;

    const stats = data as StatsDTO;
    return (
        typeof stats.clubCount === 'number' &&
        typeof stats.showCount === 'number' &&
        typeof stats.comedianCount === 'number' &&
        stats.clubCount >= 0 &&
        stats.showCount >= 0 &&
        stats.comedianCount >= 0
    );
}

