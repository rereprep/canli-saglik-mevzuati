// macOS Vision OCR (JXA). Kullanım: osascript -l JavaScript araclar/ocr_vision.js <çıktı_klasörü> <png...>
ObjC.import('Foundation');
ObjC.import('Vision');
ObjC.import('AppKit');

function run(argv) {
  var outDir = argv[0];
  var fm = $.NSFileManager.defaultManager;
  for (var i = 1; i < argv.length; i++) {
    var path = argv[i];
    var ad = path.split('/').pop().replace(/\.png$/i, '');
    var out = outDir + '/' + ad + '.json';
    if (fm.fileExistsAtPath(out)) continue;
    var url = $.NSURL.fileURLWithPath(path);
    var req = $.VNRecognizeTextRequest.alloc.init;
    req.recognitionLevel = 0; // accurate
    req.usesLanguageCorrection = true;
    req.recognitionLanguages = $(['tr-TR', 'en-US']);
    var handler = $.VNImageRequestHandler.alloc.initWithURLOptions(url, $({}));
    var err = Ref();
    var ok = handler.performRequestsError($([req]), err);
    if (!ok) { console.log('hata: ' + path); continue; }
    var res = req.results;
    var lines = [];
    for (var j = 0; j < res.count; j++) {
      var o = res.objectAtIndex(j);
      var c = o.topCandidates(1).objectAtIndex(0);
      var b = o.boundingBox;
      lines.push({text: c.string.js, x0: b.origin.x, x1: b.origin.x + b.size.width,
                  top: 1 - (b.origin.y + b.size.height), bottom: 1 - b.origin.y, conf: c.confidence});
    }
    var s = $.NSString.alloc.initWithUTF8String(JSON.stringify({lines: lines}));
    s.writeToFileAtomicallyEncodingError(out, true, 4, null);
  }
}

