# EoSim Android App

## Overview

The EoSim Android app is a native Android application built with Kotlin + Jetpack Compose that wraps the EoSim Universal Simulation Platform, providing a native mobile experience for Android devices.

## Architecture

The Android app communicates exclusively with the production API at `https://api.eosim.io` and uses WebSocket at `wss://api.eosim.io` for real-time simulation updates.

## Build Configuration

**Minimum SDK:** Android 8.0 (API 26)  
**Target SDK:** Android 15 (API 35)  
**Package ID:** `io.eosim.app`  
**Version:** 3.0.1 (Build 301)

## Key Files

| File | Purpose |
|------|---------|
| `app/build.gradle.kts` | Gradle build config |
| `app/src/main/AndroidManifest.xml` | App manifest |
| `app/src/main/java/io/eosim/app/` | Kotlin source |
| `app/src/main/res/` | Resources |

## Features

- Full access to all 20 simulation domains
- Real-time WebSocket updates from `wss://api.eosim.io`
- GPS-based API region selection (US, EU, AP)
- 10-language support with RTL (Arabic)
- Material Design 3 dark theme
- Push notifications for simulation events
- Offline mode with sync on reconnect
- Biometric authentication

## Build Instructions

```bash
cd android
./gradlew assembleRelease
# APK: app/build/outputs/apk/release/app-release.apk
```

## Play Store

Published at: https://play.google.com/store/apps/details?id=io.eosim.app
