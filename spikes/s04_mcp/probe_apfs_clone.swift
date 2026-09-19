import Foundation

struct Snapshot: Codable {
    let label: String
    let mayShareFileContent: Bool?
    let fileContentIdentifier: Int64?
    let fileResourceIdentifier: String?
}

enum ProbeError: Error {
    case expectedCloneSignalMissing
}

func snapshot(_ label: String, _ url: URL) throws -> Snapshot {
    let values = try url.resourceValues(forKeys: [
        .mayShareFileContentKey,
        .fileContentIdentifierKey,
        .fileResourceIdentifierKey,
    ])
    return Snapshot(
        label: label,
        mayShareFileContent: values.mayShareFileContent,
        fileContentIdentifier: values.fileContentIdentifier,
        fileResourceIdentifier: values.fileResourceIdentifier.map { String(describing: $0) }
    )
}

let manager = FileManager.default
let root = manager.temporaryDirectory.appendingPathComponent("pcc-s04-apfs-\(UUID().uuidString)")
try manager.createDirectory(at: root, withIntermediateDirectories: false)
defer { try? manager.removeItem(at: root) }

let source = root.appendingPathComponent("source")
let clone = root.appendingPathComponent("clone")
let rewritten = root.appendingPathComponent("rewritten")
let payload = Data("synthetic-s04-clone-probe".utf8)
try payload.write(to: source)
try manager.copyItem(at: source, to: clone)
try payload.write(to: rewritten)

let sourceBefore = try snapshot("source-before", source)
let cloneBefore = try snapshot("clone-before", clone)
let rewrittenBefore = try snapshot("rewritten-before", rewritten)

try Data("changed".utf8).write(to: clone)
let sourceAfter = try snapshot("source-after", source)
let cloneAfter = try snapshot("clone-after", clone)
let snapshots = [sourceBefore, cloneBefore, rewrittenBefore, sourceAfter, cloneAfter]

guard sourceBefore.mayShareFileContent == true,
      cloneBefore.mayShareFileContent == true,
      rewrittenBefore.mayShareFileContent == false,
      sourceBefore.fileContentIdentifier != nil,
      sourceBefore.fileContentIdentifier == cloneBefore.fileContentIdentifier,
      sourceBefore.fileContentIdentifier != rewrittenBefore.fileContentIdentifier,
      sourceAfter.fileContentIdentifier == cloneAfter.fileContentIdentifier else {
    throw ProbeError.expectedCloneSignalMissing
}

let output: [String: Any] = [
    "status": "PASS_NATIVE_SIGNAL_FOUND",
    "filesystem": try root.resourceValues(forKeys: [.volumeSupportsFileCloningKey]).volumeSupportsFileCloning as Any,
    "snapshots": try snapshots.map { snapshot in
        let data = try JSONEncoder().encode(snapshot)
        return try JSONSerialization.jsonObject(with: data)
    },
]
let data = try JSONSerialization.data(withJSONObject: output, options: [.prettyPrinted, .sortedKeys])
print(String(decoding: data, as: UTF8.self))
