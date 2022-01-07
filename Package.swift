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
            url:"https://github.com/MobileVLCKit-SPM/MobileVLCKit-SPM/releases/download/FileStorage/MobileVLCKit-3.3.15.xcframework.zip",
            checksum:"42e8360346d84734b6d35ae7f8cd2cbf11930b63989fb57e5c8a7c3b97f07b2e"
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
