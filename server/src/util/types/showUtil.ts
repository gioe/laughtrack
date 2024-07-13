export const isLikelyShow = (inputString: string, showSignifiers: string[]): boolean => {
    var isLikely = false;
    for (const singifier of showSignifiers) {
      if (inputString.toLowerCase().includes(singifier)) {
        isLikely = true;
      }
    }
    return isLikely
  }
