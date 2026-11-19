import Foundation
import AVFoundation
import AppKit
import CoreGraphics

// 用法: frame_extract <video.mp4> <outDir> <intervalSec> <minDiff> <maxFrames>
let args = CommandLine.arguments
guard args.count >= 4 else {
    print("usage: frame_extract <video> <outDir> <interval> [minDiff] [maxFrames]")
    exit(2)
}
let videoPath = args[1]
let outDir = args[2]
let interval = Double(args[3]) ?? 3.0
let minDiff = Double(args.count > 4 ? args[4] : "9.0") ?? 9.0
let maxFrames = Int(args.count > 5 ? args[5] : "400") ?? 400

try? FileManager.default.createDirectory(atPath: outDir, withIntermediateDirectories: true)

let asset = AVURLAsset(url: URL(fileURLWithPath: videoPath))
let dur = CMTimeGetSeconds(asset.duration)
guard dur.isFinite && dur > 0 else { print("ERROR duration"); exit(1) }

let gen = AVAssetImageGenerator(asset: asset)
gen.appliesPreferredTrackTransform = true
gen.maximumSize = CGSize(width: 1080, height: 1920)
gen.requestedTimeToleranceBefore = CMTime(seconds: 0.2, preferredTimescale: 600)
gen.requestedTimeToleranceAfter = CMTime(seconds: 0.2, preferredTimescale: 600)

let W = 40, H = 24
func fingerprint(_ cg: CGImage) -> ([UInt8], Double) {
    let cs = CGColorSpaceCreateDeviceGray()
    guard let ctx = CGContext(data: nil, width: W, height: H, bitsPerComponent: 8,
                              bytesPerRow: W, space: cs,
                              bitmapInfo: CGImageAlphaInfo.none.rawValue) else { return ([], 0) }
    ctx.interpolationQuality = .low
    ctx.draw(cg, in: CGRect(x: 0, y: 0, width: W, height: H))
    guard let ptr = ctx.data?.bindMemory(to: UInt8.self, capacity: W * H) else { return ([], 0) }
    let buf = Array(UnsafeBufferPointer(start: ptr, count: W * H))
    var edge = 0
    for y in 0..<H {
        for x in 1..<W {
            edge += abs(Int(buf[y * W + x]) - Int(buf[y * W + x - 1]))
        }
    }
    return (buf, Double(edge) / Double(W * (H - 1)))
}

func saveJPEG(_ cg: CGImage, _ path: String) {
    let rep = NSBitmapImageRep(cgImage: cg)
    if let data = rep.representation(using: .jpeg, properties: [.compressionFactor: 0.78]) {
        try? data.write(to: URL(fileURLWithPath: path))
    }
}

var prev: [UInt8]? = nil
var saved = 0
var lines: [String] = []
var t = 0.5
while t < dur && saved < maxFrames {
    let cm = CMTime(seconds: t, preferredTimescale: 600)
    if let cg = try? gen.copyCGImage(at: cm, actualTime: nil) {
        let (fp, edge) = fingerprint(cg)
        var diff = 999.0
        if let p = prev, p.count == fp.count {
            var s = 0
            for i in 0..<fp.count { s += abs(Int(fp[i]) - Int(p[i])) }
            diff = Double(s) / Double(fp.count)
        }
        if diff >= minDiff || prev == nil {
            let name = String(format: "f_%06.1f.jpg", t)
            saveJPEG(cg, (outDir as NSString).appendingPathComponent(name))
            lines.append(String(format: "{\"file\":\"%@\",\"t\":%.1f,\"diff\":%.2f,\"edge\":%.2f}", name, t, diff, edge))
            prev = fp
            saved += 1
        }
    }
    t += interval
}
let manifest = (outDir as NSString).appendingPathComponent("frames.json")
try? ("[" + lines.joined(separator: ",\n") + "]").write(toFile: manifest, atomically: true, encoding: .utf8)
print("DURATION \(String(format: "%.1f", dur)) SAVED \(saved)")
