"use client";

import React from "react";
import FavoriteComediansGrid from "@/ui/components/grid/favoriteComedians";

interface FavoritesTabProps {
    userId: string;
}

const FavoritesTab = ({ userId }: FavoritesTabProps) => {
    return <FavoriteComediansGrid userId={userId} />;
};

export default FavoritesTab;
