import { useEffect } from 'react';

export function useScrollPosition() {
  useEffect(() => {
    // Get stored scroll position from sessionStorage
    const savedScrollPosition = sessionStorage.getItem('scrollPosition');
    if (savedScrollPosition) {
      // Restore scroll position after a short delay to ensure content is rendered
      setTimeout(() => {
        window.scrollTo(0, parseInt(savedScrollPosition));
        // Clear the stored position after restoring
        sessionStorage.removeItem('scrollPosition');
      }, 100);
    }

    // Store scroll position before refresh/navigation
    const handleBeforeUnload = () => {
      sessionStorage.setItem('scrollPosition', window.scrollY.toString());
    };

    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, []);
}
