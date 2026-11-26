plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.jetbrains.kotlin.android)
}

android {
    namespace = "com.netmindai.node"
    compileSdk = 36

    ndkVersion = "29.0.13113456"

    defaultConfig {
        applicationId = "com.netmindai.node"

        minSdk = 28
        targetSdk = 36

        versionCode = 1
        versionName = "0.1.0-alpha.1"

        ndk {
            abiFilters += listOf("arm64-v8a", "x86_64")
        }
    }

    signingConfigs {
        create("release") {
            // NOTE: alpha-quality self-signed keystore committed for consistent
            // sideload updates. Rotate before any production release.
            storeFile = file("../netmind-alpha.jks")
            storePassword = "netmind-alpha-2026"
            keyAlias = "netmind"
            keyPassword = "netmind-alpha-2026"
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            isShrinkResources = false
            signingConfig = signingConfigs.getByName("release")
        }
        debug {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    // llama.cpp is built with GGML_BACKEND_DL=ON and dlopens its CPU variant
    // .so files from the native library dir at runtime -> they must be
    // extracted from the APK (legacy packaging).
    packaging {
        jniLibs {
            useLegacyPackaging = true
        }
    }
}

dependencies {
    implementation(libs.bundles.androidx)
    implementation(libs.material)

    implementation(project(":lib"))
}
