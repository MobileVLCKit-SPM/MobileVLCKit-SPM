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
            url:"https://github.com/MobileVLCKit-SPM/MobileVLCKit-SPM/releases/download/FileStorage/MobileVLCKit-3.1.2.xcframework.zip",
            checksum:"3306dc31a50c122153e9666ff799ee0bf3b70a41e5f326fd4f453f68c42c5087"
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
