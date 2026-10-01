---
id: 32
title: A synchronous controller cannot complete the retail asynchronous libds queue
status: resolved
symptom: retail libds advances queued ReadN work from controller interrupts and command/data callbacks
tags: cd,libds,platform-hle,re-20
created: 2026-08-24
updated: 2026-08-24
---

The host CD contract completes operations inline and models NO controller IRQ, so the guest's
asynchronous queue has no event that can make its wait condition true.

**Dead ends:** calling the executable's finite status tick to retry commands (it cannot manufacture the
missing callback transition), and fabricating a callback result. `NativeFile` therefore owns only
executable-measured finite extents: real CHD sectors, the exact requested extent, and an explicit host
field per completed copy.
