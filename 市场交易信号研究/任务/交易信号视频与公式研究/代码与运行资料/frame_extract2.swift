import Foundation
import AVFoundation
import AppKit
import CoreGraphics

// 用法: frame_extract2 <video.mp4> <outDir> <intervalSec> <mode>
// mode: probe = 只输出特征 manifest; extract = 输出特征并保存候选高清帧
let args = CommandLine.arguments
guard args.count >= 4 else { print("usage: frame_extract2 <video> <outDir> <interval> [probe|extract]"); exit(2) }
let videoPath = args[1]
let outDir = args[2]
let interval = Double(args[3]) ?? 2.0
let mode = args.count > 4 ? args[4] : "extract"

try? FileManager.default.createDirectory(atPath: outDir, withIntermediateDirectories: true)
let asset = AVURLAsset(url: URL(fileURLWithPath: videoPath))
let dur = CMTimeGetSeconds(asset.duration)
guard dur.isFinite && dur > 0 else { print("ERROR duration"); exit(1) }

let gen = AVAssetImageGenerator(asset: asset)
gen.appliesPreferredTrackTransform = true
gen.maximumSize = CGSize(width: 1080, height: 1920)
gen.requestedTimeToleranceBefore = CMTime(seconds: 0.15, preferredTimescale: 600)
gen.requestedTimeToleranceAfter = CMTime(seconds: 0.15, preferredTimescale: 600)

let W = 48, H = 32
func features(_ cg: CGImage) -> ([UInt8], Double, Double, Double, Double) {
    let cs = CGColorSpaceCreateDeviceGray()
    guard let ctx = CGContext(data: nil, width: W, height: H, bitsPerComponent: 8,
                              bytesPerRow: W, space: cs,
                              bitmapInfo: CGImageAlphaInfo.none.rawValue) else { return ([], 0, 0, 0, 0) }
    ctx.interpolationQuality = .low
    ctx.draw(cg, in: CGRect(x: 0, y: 0, width: W, height: H))
    guard let ptr = ctx.data?.bindMemory(to: UInt8.self, capacity: W * H) else { return ([], 0, 0, 0, 0) }
    let b = Array(UnsafeBufferPointer(start: ptr, count: W * H))
    var edge = 0, sum = 0, white = 0, dark = 0
    for y in 0..<H {
        for x in 0..<W {
            let v = Int(b[y * W + x])
            sum += v
            if v > 190 { white += 1 }
            if v < 60 { dark += 1 }
            if x > 0 { edge += abs(v - Int(b[y * W + x - 1])) }
        }
    }
    let n = Double(W * H)
    return (b, Double(edge) / Double(H * (W - 1)), Double(sum) / n,
            Double(white) / n, Double(dark) / n)
}

func saveJPEG(_ cg: CGImage, _ path: String, _ q: CGFloat) {
    let rep = NSBitmapImageRep(cgImage: cg)
    if let data = rep.representation(using: .jpeg, properties: [.compressionFactor: q]) {
        try? data.write(to: URL(fileURLWithPath: path))
    }
}

func diff(_ a: [UInt8], _ b: [UInt8]) -> Double {
    guard a.count == b.count, !a.isEmpty else { return 999 }
    var s = 0
    for i in 0..<a.count { s += abs(Int(a[i]) - Int(b[i])) }
    return Double(s) / Double(a.count)
}

var lines: [String] = []
var prevSaved: [UInt8]? = nil
var saved = 0
var t = 0.4
while t < dur {
    let cm = CMTime(seconds: t, preferredTimescale: 600)
    if let cg = try? gen.copyCGImage(at: cm, actualTime: nil) {
        let (fp, edge, mean, white, dark) = features(cg)
        // 白底图表/公式/截图；或深色大面积低边缘的图表页
        let lightChart = white > 0.30 || mean > 132
        let darkChart = dark > 0.55 && edge < 20 && white < 0.08
        let candidate = lightChart || darkChart
        let name = String(format: "f_%07.2f.jpg", t)
        lines.append(String(format: "{\"file\":\"%@\",\"t\":%.2f,\"edge\":%.2f,\"mean\":%.2f,\"white\":%.3f,\"dark\":%.3f,\"cand\":%@}",
                            name, t, edge, mean, white, dark, candidate ? "true" : "false"))
        if mode == "extract" && candidate {
            let d = prevSaved.map { diff(fp, $0) } ?? 999
            if d >= 7.0 {
                saveJPEG(cg, (outDir as NSString).appendingPathComponent(name), 0.85)
                prevSaved = fp
                saved += 1
            }
        }
    }
    t += interval
}
let manifest = (outDir as NSString).appendingPathComponent("frames.json")
try? ("[" + lines.joined(separator: ",\n") + "]").write(toFile: manifest, atomically: true, encoding: .utf8)
print("DURATION \(String(format: "%.1f", dur)) SAMPLED \(lines.count) SAVED \(saved)")
