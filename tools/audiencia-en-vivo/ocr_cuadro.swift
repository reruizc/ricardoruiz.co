// Lee el texto de un cuadro del video con Vision (local, gratis).
// Uso: ocr_cuadro <imagen.jpg>  → una línea por texto: "y<TAB>texto" (y=0 abajo, 1 arriba)
import Foundation
import Vision
import AppKit
let a = CommandLine.arguments
guard a.count > 1, let img = NSImage(contentsOfFile: a[1]),
      let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { exit(1) }
let req = VNRecognizeTextRequest()
req.recognitionLevel = .accurate
req.recognitionLanguages = ["es-ES"]
req.usesLanguageCorrection = false
try? VNImageRequestHandler(cgImage: cg).perform([req])
for o in (req.results ?? []) {
  if let t = o.topCandidates(1).first?.string {
    print(String(format: "%.3f\t%.3f\t%@", o.boundingBox.minY, o.boundingBox.minX, t))
  }
}
