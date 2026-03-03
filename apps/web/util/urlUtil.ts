const getBaseUrl = () => {
    if (typeof window !== 'undefined') {
        // Browser should use relative path
        return '';
    }

    // Assume localhost
    return `${process.env.NEXT_PUBLIC_WEBSITE_URL}`
};
export const getUrl = (endpoint: string, searchParams?: URLSearchParams) => {
    const baseUrl = getBaseUrl();
    let url: URL;

    try {
        // Create URL object based on environment
        if (!baseUrl) {
            // Client-side: use current origin or full endpoint
            const base = endpoint.startsWith('http')
                ? endpoint
                : `${window.location.origin}${endpoint}`;
            url = new URL(base);
        } else {
            // Server-side: combine baseUrl and endpoint
            url = new URL(endpoint, baseUrl);
        }

        // Add search parameters if provided
        if (searchParams) {
            searchParams.forEach((value, key) => {
                url.searchParams.append(key, value);
            });
        }

        return url.toString();
    } catch (error) {
        console.error('Error constructing URL:', {
            endpoint,
            baseUrl,
            searchParams: searchParams?.toString(),
            error
        });

        // Fallback attempt with production URL
        try {
            url = new URL(endpoint, 'https://www.laugh-track.com');

            if (searchParams) {
                searchParams.forEach((value, key) => {
                    url.searchParams.append(key, value);
                });
            }

            return url.toString();
        } catch (fallbackError) {
            console.error('Fallback URL construction failed:', fallbackError);
            // Return a reasonable default or throw
            return endpoint;
        }
    }
};
