pluginManagement {
    repositories {
        google {
            content {
                includeGroupByRegex("com\\.android.*")
                includeGroupByRegex("com\\.google.*")
                includeGroupByRegex("androidx.*")
            }
        }
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "LaughTrack"

include(":app")
include(":core:ui")
include(":core:navigation")
include(":core:network")
include(":core:data")
include(":core:playback")
include(":core:analytics")
include(":feature:home")
include(":feature:search")
include(":feature:library")
include(":feature:detail")
include(":feature:onboarding")
include(":feature:notifications")
include(":feature:profile")
