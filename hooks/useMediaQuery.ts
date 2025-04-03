// hooks/useMediaQuery.ts
import { useState, useEffect } from 'react';

/**
 * A hook that returns whether a media query matches the current viewport
 * @param query - A valid CSS media query string (e.g., "(max-width: 768px)")
 * @returns boolean indicating whether the media query matches
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    // Create a media query list
    const mediaQuery = window.matchMedia(query);

    // Set initial value
    setMatches(mediaQuery.matches);

    // Define a callback function for the media query change event
    const handleChange = (event: MediaQueryListEvent) => {
      setMatches(event.matches);
    };

    // Add event listener for changes
    // Use the newer addEventListener API for better compatibility
    mediaQuery.addEventListener('change', handleChange);

    // Clean up by removing the event listener when the component unmounts
    return () => {
      mediaQuery.removeEventListener('change', handleChange);
    };
  }, [query]); // Only re-run if the query changes

  return matches;
}
