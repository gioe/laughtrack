// Root build file. Plugins are declared here with `apply false` so module build
// files can apply them without re-declaring versions (resolved via the version
// catalog in gradle/libs.versions.toml).
plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.android.library) apply false
    alias(libs.plugins.kotlin.android) apply false
    alias(libs.plugins.kotlin.compose) apply false
    alias(libs.plugins.kotlin.serialization) apply false
    alias(libs.plugins.ksp) apply false
    alias(libs.plugins.hilt) apply false
    alias(libs.plugins.ktlint) apply false
    alias(libs.plugins.detekt) apply false
    // On the classpath but applied conditionally by :app (only when a
    // google-services.json is present) so a missing Firebase config never breaks
    // the build — see app/build.gradle.kts.
    alias(libs.plugins.google.services) apply false
}

// Point every module's detekt task at the shared config so static-analysis rules
// are consistent across the build (ktlint uses its own sensible defaults).
subprojects {
    plugins.withId("io.gitlab.arturbosch.detekt") {
        extensions.configure<io.gitlab.arturbosch.detekt.extensions.DetektExtension> {
            buildUponDefaultConfig = true
            config.setFrom(rootProject.files("config/detekt/detekt.yml"))
        }
    }
}
