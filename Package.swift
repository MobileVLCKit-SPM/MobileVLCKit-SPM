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
            url:"https://github.com/MobileVLCKit-SPM/MobileVLCKit-SPM/releases/download/FileStorage/MobileVLCKit-3.3.5.xcframework.zip",
            checksum:"1ab40bb5dd93876272ebab90258977f002008840091b3bac0b284d4396775738"
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
