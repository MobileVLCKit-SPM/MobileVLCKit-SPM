// swift-tools-version:5.3

import PackageDescription

let package = Package(
    name: "MobileVLCKit",
    platforms: [
        .iOS(.v12),
    ],
    products: [
        .library(name: "MobileVLCKit", targets: ["MobileVLCKit"]),
        .library(name: "MobileVLCKitSampleViewController", targets: ["MobileVLCKitSampleViewController"])
    ],
    targets: [
        .binaryTarget(
            name: "MobileVLCKit",
            url:"https://github.com/MobileVLCKit-SPM/MobileVLCKit-SPM/releases/download/FileStorage/MobileVLCKit-3.3.1.xcframework.zip",
            checksum:"52816ea5360a44311c4b1933e9af0063523a8750e3f947d9c25c17d17f0e83d1"
        ),
        .target(
            name: "MobileVLCKitSampleViewController",
            dependencies: [
                "MobileVLCKit"
            ],
            path: "Sample"
        ),
    ]
)
