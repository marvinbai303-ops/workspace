import Foundation
import AVFoundation

// usage: extract_audio <in.mp4> <out.m4a>
let a = CommandLine.arguments
guard a.count >= 3 else { print("usage: extract_audio <in> <out>"); exit(2) }
let inURL = URL(fileURLWithPath: a[1])
let outURL = URL(fileURLWithPath: a[2])
try? FileManager.default.removeItem(at: outURL)

let asset = AVURLAsset(url: inURL)
guard let session = AVAssetExportSession(asset: asset, presetName: AVAssetExportPresetAppleM4A) else {
    print("FAIL no session"); exit(1)
}
session.outputURL = outURL
session.outputFileType = .m4a
let sem = DispatchSemaphore(value: 0)
session.exportAsynchronously { sem.signal() }
sem.wait()
if session.status == .completed {
    let attrs = try? FileManager.default.attributesOfItem(atPath: a[2])
    let sz = (attrs?[.size] as? Int) ?? 0
    print("OK \(sz) bytes")
} else {
    print("FAIL status=\(session.status.rawValue) err=\(String(describing: session.error))")
}
