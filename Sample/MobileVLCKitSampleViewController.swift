//
//  File.swift
//
//
//  Created by ^-^ on 2022/1/5.
//

import Foundation
import UIKit
import MobileVLCKit

class MobileVLCKitSampleViewController:UIViewController{
    let mediaURL = "https://streams.videolan.org/streams/mp4/Mr_MrsSmith-h264_aac.mp4"

    @IBOutlet weak var movieView: UIView!

    var mediaPlayer = VLCMediaPlayer()

    override func viewDidLoad() {
        super.viewDidLoad()
        setupMediaPLayer()
    }
    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        mediaPlayer.play()
    }

    func setupMediaPLayer() {
        mediaPlayer.delegate = self
        mediaPlayer.drawable = movieView
        mediaPlayer.media = VLCMedia(url: URL(string: mediaURL)!)
    }

    @IBAction func handlePlayPause(_ sender: UIButton) {
        if mediaPlayer.isPlaying {
            mediaPlayer.pause()
            sender.isSelected = true
        } else {
            mediaPlayer.play()
            sender.isSelected = false
        }
    }
}

extension MobileVLCKitSampleViewController: VLCMediaPlayerDelegate {

    func mediaPlayerStateChanged(_ aNotification: Notification!) {
        if mediaPlayer.state == .stopped {
            self.dismiss(animated: true, completion: nil)
        }
    }
}
