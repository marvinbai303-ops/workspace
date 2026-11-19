import Foundation
import AppKit

// 用法: make_sheet <framesDir> <out.jpg> [cols] [cellW]
let a = CommandLine.arguments
guard a.count >= 3 else { print("usage: make_sheet <framesDir> <out.jpg> [cols] [cellW]"); exit(2) }
let dir = a[1], out = a[2]
let cols = Int(a.count > 3 ? a[3] : "6") ?? 6
let cellW = Int(a.count > 4 ? a[4] : "200") ?? 200

let fm = FileManager.default
var names = (try? fm.contentsOfDirectory(atPath: dir))?
    .filter { $0.hasSuffix(".jpg") && $0.hasPrefix("t_") }.sorted() ?? []
if a.count > 5, let s = Int(a[5]) { names = Array(names.dropFirst(s)) }
if a.count > 6, let n = Int(a[6]) { names = Array(names.prefix(n)) }
guard !names.isEmpty else { print("NO_FRAMES"); exit(1) }

let cellH = Int(Double(cellW) * 16.0 / 9.0) + 26
let rows = (names.count + cols - 1) / cols
let W = cols * cellW, H = rows * cellH
guard let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: W, pixelsHigh: H,
                                 bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true,
                                 isPlanar: false, colorSpaceName: .deviceRGB,
                                 bytesPerRow: 0, bitsPerPixel: 0) else { exit(1) }
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
NSColor(calibratedWhite: 0.16, alpha: 1).setFill()
NSRect(x: 0, y: 0, width: W, height: H).fill()

let attrs: [NSAttributedString.Key: Any] = [
    .font: NSFont.monospacedSystemFont(ofSize: 13, weight: .medium),
    .foregroundColor: NSColor.white
]
for (i, name) in names.enumerated() {
    let c = i % cols, r = i / cols
    let x = c * cellW, y = r * cellH
    let imgRect = NSRect(x: x + 2, y: y + 24, width: cellW - 4, height: cellH - 28)
    if let im = NSImage(contentsOfFile: (dir as NSString).appendingPathComponent(name)) {
        im.draw(in: imgRect, from: .zero, operation: .copy, fraction: 1.0)
    }
    let label = name.replacingOccurrences(of: "t_", with: "").replacingOccurrences(of: ".jpg", with: "")
    (label as NSString).draw(at: NSPoint(x: x + 6, y: y + 4), withAttributes: attrs)
}
NSGraphicsContext.restoreGraphicsState()
if let data = rep.representation(using: .jpeg, properties: [.compressionFactor: 0.82]) {
    try? data.write(to: URL(fileURLWithPath: out))
}
print("SHEET \(W)x\(H) frames \(names.count)")
