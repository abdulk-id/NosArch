# Task Priority Guidelines

Priorities are determined solely by **urgency × impact**.

## P1 — Critical

A task qualifies as P1 when the system is actively impaired or at risk. Triggers:

- **System cannot boot, login, or launch the window manager.**
- **Data loss risk** — backups, snapshots, swap, or critical storage is broken or missing.
- **Daily-driver core is broken** — an essential feature used in every session is completely inoperable (e.g., launcher, key bindings, window management).
- **Active security exploit** with no available workaround.
- **Prerequisite** that blocks all other meaningful P1 or P2 work.

> _"Using the system is noticeably impaired every single session."_

## P2 — Important

A task qualifies as P2 when the system functions correctly but has meaningful room for improvement. Triggers:

- **Feature is broken but low-impact** — an annoyance or workaround exists (e.g. an option that silently fails).
- **Non-critical bug** — the feature works but behaves unexpectedly without stopping normal flow.
- **Security hardening** — best-practice improvement with no active exploit.
- **Meaningful quality-of-life improvement** that would make daily use smoother.
- **New capability** that meaningfully changes how you interact with the system.

> _"The system works fine; this would make it noticeably better."_

## P3 — Nice-to-have

A task qualifies as P3 when it is cosmetic, experimental, or otherwise low-impact. Triggers:

- **Cosmetic changes** — fonts, cursors, colors, wallpapers, or any purely visual tweak.
- **Extension of a working feature** — additional controls, configuration options, or extensions on top of something that already works.
- **Exploratory ideas** — such as future technology (e.g., Quickshell).
- **Low-impact polish** that will not affect daily rhythm.

> _"The system is fine without this. Tinker when time permits."_

---

## Decision Flow

```
Is boot, login, or core WM broken?                          → P1
Is there a risk of data loss?                               → P1
Is a daily essential feature completely inoperable?         → P1
Is there an active exploit with no workaround?              → P1
Is this a prerequisite blocking other P1/P2 work?           → P1

Is a feature broken but low-impact (annoying, workaround)?  → P2
Would this meaningfully improve daily workflow?             → P2
Is this security hardening (no active exploit)?             → P2

Is this cosmetic, experimental, or a low-impact extension?  → P3
```

---

## Notes

- Priority must be reassessed periodically. A P3 task may become P2 or P1 if the system changes or the task becomes a prerequisite for other work.
- A single task may fit multiple triggers; assign the highest applicable priority.
- Leve of effort, implementation complexity, and personal interest must not factor into priority level.
