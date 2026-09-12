---
id: 36
title: Resident image mapping had no title-owned boundary after static removal
status: resolved
symptom: The break-first migration removed the generated product, but no Vagrant-owned runtime seam admitted the measured resident PS-X image to psxport's image catalog.
tags: S015,RE-02,dynarec,image-identity,boot
created: 2026-09-12
updated: 2026-09-12
---

## Root cause

The old static launcher supplied image mapping as part of its generated boot path. Removing that
path correctly left gameplay unavailable, but the replacement title adapter had not yet claimed the
resident header contract or the framework's image publication call.

## Fix

`vagrant::VagrantRuntime::loadResidentImage` checks the measured `SLUS_010.40` PS-X header before
delegating to psxport's `loadPsxExeImage`. The framework therefore remains the sole owner of image
catalog generations, executable-write invalidation, and memory publication. The title-owned
`vagrant_image_contract` test proves accepted entry/range registration and refuses a changed entry.

## Remaining boundary

The test uses a synthetic PS-X shape. Complete-file SHA authentication, overlay generation
replacement, native override registration, and real resident execution through Lightrec remain open
under RE-02/S015.
