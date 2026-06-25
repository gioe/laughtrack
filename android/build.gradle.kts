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
        // The OpenAPI client under core/network/.../generated is emitted verbatim
        // by openapi-generator and committed unmodified — the drift check diffs it
        // against a clean regen, so it must NOT be reformatted. Keep static
        // analysis off generated sources.
        tasks.withType<io.gitlab.arturbosch.detekt.Detekt>().configureEach {
            exclude("**/generated/**")
        }
    }

    // Same rationale for ktlint: the generated client is raw generator output
    // (trailing KDoc whitespace, generator-ordered imports) that intentionally
    // diverges from the project's ktlint style. Linting it would force edits that
    // the drift check then rejects — and ktlint cannot even parse some generated
    // files. Exclude the generated package from every ktlint source-set task.
    plugins.withId("org.jlleitschuh.gradle.ktlint") {
        extensions.configure<org.jlleitschuh.gradle.ktlint.KtlintExtension> {
            filter {
                exclude { it.file.path.contains("/generated/") }
            }
        }
    }
}
