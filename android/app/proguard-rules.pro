# ProGuard / R8 rules for the release build.
# Hilt, Compose, and OkHttp/Retrofit ship their own consumer rules, so this file
# starts minimal. Add app-specific keep rules here as obfuscation surfaces them.

# Keep kotlinx.serialization generated serializers.
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.**
-keepclassmembers class **$$serializer { *; }
