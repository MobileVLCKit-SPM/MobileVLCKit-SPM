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
            url:"https://github.com/MobileVLCKit-SPM/MobileVLCKit-SPM/releases/download/FileStorage/MobileVLCKit-3.3.17.xcframework.zip",
            checksum:"0eee762797551d078209a72525deb52965dcd6bd098089f6efa2485eac999c2d"
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
