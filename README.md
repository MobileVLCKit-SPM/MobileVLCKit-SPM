#  MobileVLCKit swift package support
This project auto conver mobilevlckit from : https://download.videolan.org/pub/cocoapods/prod to swift 

# full support 
MobileVLCKit with full dSYMs and simulator support (zip file size upto 1~2G)
https://github.com/MobileVLCKit-SPM/MobileVLCKit-SPM
```
dependencies: [
  .package(url: "https://github.com/MobileVLCKit-SPM/MobileVLCKit-SPM", from: "3.5.1"),
]
...
targets: [
          .target(
              ...
              dependencies: [
                .product(name: "MobileVLCKit", package: "MobileVLCKit-SPM",condition: TargetDependencyCondition.when(platforms: [.iOS])),
              ],
             ...
           )
        ]
)
```

# lite support 
MobileVLCKit without dSYMs and simulator support (zip file size will about 200m+ )
[https://github.com/MobileVLCKit-SPM/MobileVLCKit-SPM](https://github.com/MobileVLCKit-SPM/MobileVLCKit-SPM-Lite)
```
dependencies: [
  .package(url: "https://github.com/MobileVLCKit-SPM/MobileVLCKit-SPM-Lite", from: "3.5.1"),
]
...
targets: [
          .target(
              ...
              dependencies: [
                .product(name: "MobileVLCKit", package: "MobileVLCKit-SPM-Lite",condition: TargetDependencyCondition.when(platforms: [.iOS])),
              ],
             ...
           )
        ]
)
```
