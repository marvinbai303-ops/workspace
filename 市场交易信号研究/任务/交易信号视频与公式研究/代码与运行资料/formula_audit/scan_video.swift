import Foundation
import AVFoundation
import Vision
import AppKit

let base = URL(fileURLWithPath: CommandLine.arguments[1])
let ids = Set(CommandLine.arguments.dropFirst(2).compactMap { Int($0) })
let manifestData = try Data(contentsOf: base.appendingPathComponent("video_manifest.json"))
let manifest = try JSONSerialization.jsonObject(with: manifestData) as! [String:[String:Any]]
let rows = manifest.values.sorted { ($0["idx"] as! Int) < ($1["idx"] as! Int) }
let out = base.appendingPathComponent("formula_audit/ocr")
try FileManager.default.createDirectory(at: out, withIntermediateDirectories: true)
for row in rows {
 let idx = row["idx"] as! Int
 if !ids.isEmpty && !ids.contains(idx) { continue }
 let dest = out.appendingPathComponent(String(format:"%02d.jsonl",idx))
 if FileManager.default.fileExists(atPath: dest.path) { continue }
 FileManager.default.createFile(atPath: dest.path, contents: nil)
 let fh = try FileHandle(forWritingTo: dest)
 let asset = AVURLAsset(url: base.appendingPathComponent("videos/" + (row["file"] as! String)))
 let gen = AVAssetImageGenerator(asset:asset)
 gen.appliesPreferredTrackTransform = true
 gen.maximumSize = CGSize(width: 900,height:1600)
 gen.requestedTimeToleranceBefore = CMTime(seconds:0.08,preferredTimescale:600)
 gen.requestedTimeToleranceAfter = CMTime(seconds:0.08,preferredTimescale:600)
 let duration = row["duration"] as! Double
 let start = Date()
 for t in stride(from:0.0,to:duration,by:2.0) {
  autoreleasepool {
   do {
    let img = try gen.copyCGImage(at: CMTime(seconds:t,preferredTimescale:600),actualTime:nil)
    let req = VNRecognizeTextRequest()
    req.recognitionLanguages = ["zh-Hans","en-US"]
    req.recognitionLevel = .accurate
    req.usesLanguageCorrection = false
    try VNImageRequestHandler(cgImage:img,options:[:]).perform([req])
    let text = (req.results ?? []).compactMap { obs -> [String:Any]? in
      guard let cand = obs.topCandidates(1).first else {return nil}
      return ["text":cand.string,"confidence":cand.confidence,"box":[obs.boundingBox.minX,obs.boundingBox.minY,obs.boundingBox.width,obs.boundingBox.height]]
    }
    let data = try JSONSerialization.data(withJSONObject:["idx":idx,"id":row["id"]!,"t":t,"lines":text],options:[.sortedKeys,.withoutEscapingSlashes])
    fh.write(data); fh.write(Data([10]))
    if Int(t) % 10 == 0 {
      let thumb = NSBitmapImageRep(cgImage:img)
      if let jpg = thumb.representation(using:.jpeg,properties:[.compressionFactor:0.4]) {
       let dir = base.appendingPathComponent(String(format:"formula_audit/thumbs/%02d",idx))
       try FileManager.default.createDirectory(at:dir,withIntermediateDirectories:true)
       try jpg.write(to:dir.appendingPathComponent(String(format:"%05d.jpg",Int(t))))
      }
    }
   } catch { print("ERR \(idx) \(t) \(error)") }
  }
 }
 try fh.close()
 print(String(format:"DONE %02d %.1fs",idx,Date().timeIntervalSince(start)))
 fflush(stdout)
}
