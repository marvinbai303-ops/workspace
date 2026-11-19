import Foundation
import AVFoundation
import AppKit
import CoreGraphics

// 用法: frame_extract3 <video.mp4> <outDir> <timesFile>
let args = CommandLine.arguments
guard args.count >= 4 else { print("usage: frame_extract3 <video> <outDir> <timesFile>"); exit(2) }
let videoPath = args[1]
let outDir = args[2]
let timesFile = args[3]
try? FileManager.default.createDirectory(atPath: outDir, withIntermediateDirectories: true)

guard let raw = try? String(contentsOfFile: timesFile, encoding: .utf8) else { print("ERROR times"); exit(1) }
let times = raw.split(separator: "\n").compactMap { Double($0.trimmingCharacters(in: .whitespaces)) }

let asset = AVURLAsset(url: URL(fileURLWithPath: videoPath))
let dur = CMTimeGetSeconds(asset.duration)
let gen = AVAssetImageGenerator(asset: asset)
gen.appliesPreferredTrackTransform = true
gen.maximumSize = CGSize(width: 1080, height: 1920)
gen.requestedTimeToleranceBefore = CMTime(seconds: 0.1, preferredTimescale: 600)
gen.requestedTimeToleranceAfter = CMTime(seconds: 0.1, preferredTimescale: 600)

let W = 48, H = 32
func features(_ cg: CGImage) -> ([UInt8], Double, Double, Double) {
    let cs = CGColorSpaceCreateDeviceGray()
    guard let ctx = CGContext(data: nil, width: W, height: H, bitsPerComponent: 8,
                              bytesPerRow: W, space: cs,
                              bitmapInfo: CGImageAlphaInfo.none.rawValue) else { return ([], 0, 0, 0) }
    ctx.interpolationQuality = .low
    ctx.draw(cg, in: CGRect(x: 0, y: 0, width: W, height: H))
    guard let ptr = ctx.data?.bindMemory(to: UInt8.self, capacity: W * H) else { return ([], 0, 0, 0) }
    let b = Array(UnsafeBufferPointer(start: ptr, count: W * H))
    var edge = 0, sum = 0, white = 0
    for y in 0..<H {
        for x in 0..<W {
            let v = Int(b[y * W + x]); sum += v
            if v > 190 { white += 1 }
            if x > 0 { edge += abs(v - Int(b[y * W + x - 1])) }
        }
    }
    let n = Double(W * H)
    return (b, Double(edge) / Double(H * (W - 1)), Double(sum) / n, Double(white) / n)
}

func diff(_ a: [UInt8], _ b: [UInt8]) -> Double {
    guard a.count == b.count, !a.isEmpty else { return 999 }
    var s = 0
    for i in 0..<a.count { s += abs(Int(a[i]) - Int(b[i])) }
    return Double(s) / Double(a.count)
}

var lines: [String] = []
var prev: [UInt8]? = nil
var saved = 0
for t in times where t < dur {
    let cm = CMTime(seconds: t, preferredTimescale: 600)
    guard let cg = try? gen.copyCGImage(at: cm, actualTime: nil) else { continue }
    let (fp, edge, mean, white) = features(cg)
    let name = String(format: "t_%07.2f.jpg", t)
    lines.append(String(format: "{\"file\":\"%@\",\"t\":%.2f,\"edge\":%.2f,\"mean\":%.2f,\"white\":%.3f}",
                        name, t, edge, mean, white))
    // 与上一帧几乎相同则跳过存图，保留 manifest 记录
    let d = prev.map { diff(fp, $0) } ?? 999
    if d >= 3.0 {
        let rep = NSBitmapImageRep(cgImage: cg)
        if let data = rep.representation(using: .jpeg, properties: [.compressionFactor: 0.86]) {
            try? data.write(to: URL(fileURLWithPath: (outDir as NSString).appendingPathComponent(name)))
        }
        saved += 1
    }
    prev = fp
}
try? ("[" + lines.joined(separator: ",\n") + "]").write(
    toFile: (outDir as NSString).appendingPathComponent("frames.json"), atomically: true, encoding: .utf8)
print("DURATION \(String(format: "%.1f", dur)) REQUESTED \(times.count) SAVED \(saved)")
