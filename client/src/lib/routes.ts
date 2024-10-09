export const PUBLIC_ROUTES = {
    REGISTER: '/auth/register/',
    LOGIN: '/auth/login/',
    REFRESH_TOKEN: '/auth/refresh',

    // Clubs
    GET_CLUB_DETAILS: '/api/club',
    GET_ALL_CLUBS: '/api/club/all',
    GET_TRENDING_CLUBS: '/api/club/trending',

    // Cities
    GET_CITIES: '/api/club/cities',

    // Comedians
    GET_COMEDIAN_DETAILS: '/api/comedian',
    GET_ALL_COMEDIANS: '/api/comedian/all',
    GET_TRENDING_COMEDIANS: '/api/comedian/trending',
    GET_FAVORITE_COMEDIANS: '/api/comedian/favorite/all',
    UPDATE_SOCIAL_DATA: '/api/comedian/social',

    // Shows
    GET_SHOW_DETAILS: '/api/show',
    GET_ALL_SHOWS: '/api/show/all',
    GET_TRENDING_SHOWS: '/api/show/trending',
    GET_FAVORITE_SHOWS: '/api/show/favorite/all',

    // Action
    FAVORITE_COMEDIAN: '/api/comedian/addToFavorites',
    FAVORITE_SHOW: '/api/show/favorite',
    FAVORITE_CLUB:  '/api/club/favorite',

    // Search
    HOME_SEARCH: '/api/search'
}
