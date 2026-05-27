# EoSim iOS App

## Overview

The EoSim iOS app is a native Swift + SwiftUI application for iPhone and iPad, connecting to the production API at `https://api.eosim.io`.

## Requirements

- Xcode 15.2+
- iOS 16.0+ / iPadOS 16.0+
- Swift 5.9+

## Build Configuration

**Bundle ID:** `io.eosim.app`  
**Version:** 3.0.1 (Build 301)  
**Deployment Target:** iOS 16.0

## Production Endpoints

All API calls go to `https://api.eosim.io`. The app uses App Transport Security (ATS) to enforce HTTPS only.

## Features

- All 20 simulation domains
- Real-time WebSocket from `wss://api.eosim.io`
- GPS-based API region selection
- 10-language support with RTL (Arabic)
- SwiftUI dark theme
- Face ID / Touch ID authentication
- Push notifications via APNs
- Widget extension for quick simulation status
- Siri Shortcuts integration

## Build Instructions

```bash
cd ios
xcodebuild -project EoSim.xcodeproj -scheme EoSim -configuration Release archive
```

## App Store

Published at: https://apps.apple.com/app/eosim/id0000000000
