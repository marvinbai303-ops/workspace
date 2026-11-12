import Foundation
import Vision
import AppKit
let list = try String(contentsOfFile:CommandLine.arguments[1],encoding:.utf8).split(separator:"\n")
let dest = CommandLine.arguments[2]
FileManager.default.createFile(atPath:dest,contents:nil)
let out = try FileHandle(forWritingTo:URL(fileURLWithPath:dest))
for (i,path) in list.enumerated() {
 autoreleasepool {
  do {
   let req = VNRecognizeTextRequest()
   req.usesCPUOnly = true
   req.recognitionLanguages=["zh-Hans","en-US"]
   req.recognitionLevel = .accurate
   req.usesLanguageCorrection=false
   try VNImageRequestHandler(url:URL(fileURLWithPath:String(path)),options:[:]).perform([req])
   let lines = (req.results ?? []).compactMap { o -> [String:Any]? in
    guard let c=o.topCandidates(1).first else{return nil}
    return ["text":c.string,"confidence":c.confidence,"box":[o.boundingBox.minX,o.boundingBox.minY,o.boundingBox.width,o.boundingBox.height]]
   }
   let data=try JSONSerialization.data(withJSONObject:["path":String(path),"lines":lines],options:[.sortedKeys,.withoutEscapingSlashes])
   out.write(data);out.write(Data([10]))
  } catch { print("ERROR \(path): \(error)") }
 }
 if i % 100 == 0 {print("DONE \(i)/\(list.count)");fflush(stdout)}
}
try out.close()
