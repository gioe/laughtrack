export const PUBLIC_ROUTES = {
    LOGIN: "/api/auth/login/",

    // Token
    REFRESH_TOKEN: "/api/token/refresh",

    // Clubs
    CLUB_DETAIL: `/api/club/`,
    GET_ALL_CLUBS: "/api/club/all",
    GET_TRENDING_CLUBS: "/api/club/trending",
    CLEAR_CLUB: "/api/club/clear",
    CLUB_SEARCH: "/api/club/search",

    // Cities
    GET_CITIES: "/api/club/cities",

    // Comedians
    COMEDIAN_DETAIL: `/api/comedian/`,
    GET_ALL_COMEDIANS: "/api/comedian/all",
    GET_ALL_COMEDIAN_FILTERS: "/api/comedian/filters/all",
    GET_TRENDING_COMEDIANS: "/api/comedian/trending",
    GET_FAVORITE_COMEDIANS: "/api/comedian/favorite/all",
    UPDATE_SOCIAL_DATA: "/api/comedian/social",
    MERGE_COMEDIANS: "/api/comedian/merge",
    UPDATE_COMEDIAN_TAGS: "/api/comedian/tag",
    COMEDIAN_SEARCH: "/api/comedian/search",

    // Shows
    GET_SHOW_DETAILS: "/api/show",
    SHOW_DETAIL: `/api/show/`,
    SHOW_SEARCH: "/api/show/search",
    GET_TRENDING_SHOWS: "/api/show/trending",
    GET_FAVORITE_SHOWS: "/api/show/favorite/all",
    UPDATE_SHOW_TAGS: "/api/show/tag",
    UPDATE_SHOW_LINEUP: "/api/show/lineup",

    // Tags
    GET_SHOW_TAGS: "/api/show/tags/all",
    GET_COMEDIAN_TAGS: "/api/comedian/tags/all",
    GET_CLUB_TAGS: "/api/club/tag/all",

    // Action
    FAVORITE_COMEDIAN: "/api/comedian/addToFavorites",
    FAVORITE_SHOW: "/api/show/favorite",
    FAVORITE_CLUB: "/api/club/favorite",

    // Search
    HOME_SEARCH: "/api/search",

    // Scrape
    SCRAPE: "/api/scrape",
};
