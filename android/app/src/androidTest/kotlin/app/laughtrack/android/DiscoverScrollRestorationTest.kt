package app.laughtrack.android

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasClickAction
import androidx.compose.ui.test.hasContentDescription
import androidx.compose.ui.test.hasTestTag
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollToNode
import app.laughtrack.android.core.network.ApiClientModule
import app.laughtrack.android.core.network.generated.infrastructure.ApiClient
import app.laughtrack.android.core.ui.theme.LaughTrackTheme
import app.laughtrack.android.feature.home.HOME_DISCOVER_LIST_TEST_TAG
import dagger.hilt.android.testing.BindValue
import dagger.hilt.android.testing.HiltAndroidRule
import dagger.hilt.android.testing.HiltAndroidTest
import dagger.hilt.android.testing.UninstallModules
import okhttp3.OkHttpClient
import okhttp3.Request
import org.junit.Before
import org.junit.Rule
import org.junit.Test

@HiltAndroidTest
@UninstallModules(ApiClientModule::class)
class DiscoverScrollRestorationTest {
    @BindValue
    @JvmField
    val fixtureApiClient =
        ApiClient(
            baseUrl = "http://10.0.2.2:8765/api/v1/",
            okHttpClientBuilder = OkHttpClient.Builder(),
        )

    @BindValue
    @JvmField
    @javax.inject.Named("apiBaseUrl")
    val fixtureApiBaseUrl = "http://10.0.2.2:8765/api/v1/"

    @get:Rule(order = 0)
    val hiltRule = HiltAndroidRule(this)

    @get:Rule(order = 1)
    val composeRule = createAndroidComposeRule<HiltTestActivity>()

    @Before
    fun setUp() {
        hiltRule.inject()
        OkHttpClient()
            .newCall(
                Request.Builder()
                    .url("http://10.0.2.2:8765/fixture/configure?mode=fallback-focused")
                    .build(),
            ).execute()
            .use { response ->
                check(response.isSuccessful) { "Fixture configuration failed: ${response.code}" }
            }
    }

    @Test
    fun discover_restores_deep_rail_after_returning_from_detail() {
        composeRule.setContent {
            LaughTrackTheme { AppShell() }
        }

        composeRule.waitUntil(timeoutMillis = 30_000) {
            composeRule.onAllNodes(hasTestTag(HOME_DISCOVER_LIST_TEST_TAG)).fetchSemanticsNodes().isNotEmpty()
        }
        composeRule
            .onNodeWithTag(HOME_DISCOVER_LIST_TEST_TAG)
            .performScrollToNode(hasText("Popular clubs"))
        composeRule.onNodeWithText("Popular clubs").assertIsDisplayed()

        composeRule.onAllNodes(hasClickAction() and hasText("The Comedy Store"))[0].performClick()
        composeRule.waitUntil(timeoutMillis = 30_000) {
            composeRule.onAllNodes(hasContentDescription("Back")).fetchSemanticsNodes().isNotEmpty()
        }
        composeRule.onNodeWithContentDescription("Back").performClick()

        composeRule.onNodeWithText("Popular clubs").assertIsDisplayed()
    }
}
