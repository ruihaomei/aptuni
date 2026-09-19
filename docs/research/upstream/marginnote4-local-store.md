# Upstream Research: MarginNote 4 local store

> Researched 2026-09-19 on the maintainer's Mac (MarginNote 4.4.6 build 44602, macOS 26.2), read-only,
> counts only. PRD refs: §8, §22, §25. Decision: ADR-0015.

## Where the data lives

- Container: `~/Library/Containers/QReader.MarginStudy.easy/Data/`.
- Library: `Library/Private Documents/MN4NotebookDatabase/<n>/MarginNotes.sqlite`, a Core Data SQLite
  store in WAL mode (about 900 MB here). Siblings include `MNFTS0005.sqlite` (full-text), `MNPage0001`,
  `MNVector0003`, `MNGlobal0001`, `BackupSnapshots_v4.sqlite` and `BackupStorage/`.
- Core Data metadata (`Z_METADATA.Z_PLIST`) carries `NSStoreModelVersionHashesDigest`, which identifies
  the model layout, and `Z_UUID` for the store. Entities: Activity, Book, BookComment, BookConfig,
  BookNote, BookNoteSync, BookTag, EpubRange, Media, Setting, Topic, User.

## Tables used

| Table | Columns | Meaning |
|---|---|---|
| `ZTOPIC` | `ZTOPICID`, `ZTITLE` | notebooks (1,896 here) |
| `ZBOOKNOTE` | `ZNOTEID`, `ZTOPICID`, `Z_OPT` | cards (83,096); native UUID, notebook, Core Data save counter |
| | `ZNOTETITLE`, `ZHIGHLIGHT_TEXT` | card title (25,315 titled, 17,015 of them ≤20 chars), excerpt text |
| | `ZMINDLINKS` | ordered child UUIDs joined by `|` (8,857 parents, 21,690 children; 2 cross-notebook links) |
| | `ZGROUPNOTEID` | card an excerpt is merged into (29,238; never a mind-map node) |
| | `ZNOTES` | NSKeyedArchiver comment blob; only its presence is used |
| | `ZNOTE_DATE`, `ZHIGHLIGHT_DATE` | Core Data seconds since 2001-01-01 |
| | `ZBOOKMD5`, `ZSTARTPAGE`, `ZENDPAGE` | source document (64-char `ZBOOK.ZMD5LONG`) and pages |
| `ZBOOK` | `ZMD5`, `ZMD5LONG`, `ZFILE`, `ZPATH` | documents; `ZFILE` holds the file name |

A minimized full read (titles ≤80 characters, excerpt heads ≤48) of every card takes about 3.6 s.

## Backups

`BackupSnapshots_v4.sqlite` snapshots are incremental: only 488 of 998 store every note, and
`note_count` holds the true total. Backup history suits evaluation (S05B), not live sync.

## Access and privacy

- Touching the container triggers macOS's "access data from other apps" privacy prompt (TCC). Until
  it is answered, the calling process sleeps with about 0 CPU, so Aptuni probes in a child process
  with a timeout. Denial surfaces as `PermissionError`.
- Read-only access: `mode=ro` URI plus `PRAGMA query_only`, and one read transaction per sync. As a
  normal WAL reader, SQLite may update the `-shm` index; the database and WAL are never written.

## Links and add-ons

- The installed app registers the URL schemes `marginnote4app`, `marginnote3app` and
  `marginnote4clouddrive`. MarginNote documents card links in the form
  `marginnote3app://note/<NOTEID>`; the MN4 form `marginnote4app://note/<ZNOTEID>` is inferred and was
  not opened, to avoid switching the user's app.
- The official add-on API is JavaScript through JSBridge, with a preview developer guide
  (<http://docs.test.marginnote.cn/en/guide/>) and type definitions (<https://github.com/marginnoteapp/Addon>,
  <https://github.com/marginnoteapp/marginnote-api>). It is the fallback when direct access is not
  possible (iPadOS, schema drift). Community bridges exist (OhMyMN; `LiuWhale/marginnote-assistant`).
- OPML: MarginNote 4 ships only a bundled user-guide OPML (`text`, `video`, `info`; no node ID). Current
  documentation does not clearly expose OPML as a native export.
