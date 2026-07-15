package app.laughtrack.android.feature.search.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.laughtrack.android.core.data.favorites.FavoritesRepository
import app.laughtrack.android.core.data.favorites.FavoritesSnapshot
import app.laughtrack.android.feature.search.model.SearchFavoriteTarget
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

/** Connects search-row hearts to the same optimistic favorite state as detail and library screens. */
@HiltViewModel
class SearchFavoritesViewModel
    @Inject
    constructor(
        private val favoritesRepository: FavoritesRepository,
    ) : ViewModel() {
        val snapshot: StateFlow<FavoritesSnapshot> =
            favoritesRepository.snapshot.stateIn(
                viewModelScope,
                SharingStarted.WhileSubscribed(5_000),
                FavoritesSnapshot(),
            )

        fun setFavorite(
            target: SearchFavoriteTarget,
            isFavorite: Boolean,
        ) {
            viewModelScope.launch {
                when (target) {
                    is SearchFavoriteTarget.Comedian ->
                        favoritesRepository.setComedianFavorite(target.uuid, isFavorite)
                    is SearchFavoriteTarget.Podcast ->
                        favoritesRepository.setPodcastFavorite(target.id, isFavorite)
                }
            }
        }
    }
