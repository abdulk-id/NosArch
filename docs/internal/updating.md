# Updating (INCOMPLETE & UNCHECKED)

How a machine running an older NosArch gets to a newer one, what that covers today, and what
it does not yet.

## What an update is

There is no update command. A user pulls the repo and runs `decman`, and decman converges the
machine onto whatever the new revision declares:

- **Packages** are installed and removed until the set matches.
- **Files** are written and deleted until the set matches. Removing a declaration removes the
  file (`core/file_manager.py:113`), so there is no cleanup step to write.
- **Units** are enabled and disabled until the set matches.
- **`on_change` hooks** then reload whatever needed reloading.

The important property is that this is _convergence_, not a sequence of steps. decman does
not know or care which version the machine was on. It reads the current state, compares it to
the declared state, and closes the difference. A user three versions behind and a user one
version behind run exactly the same code path, and a fresh install is the same path again
with more to do.

This is why NosArch has no migration scripts, and why it needs far fewer of them than a
system built on imperative install steps.

## What convergence does not cover

decman manages what it declares. Three kinds of state fall outside that.

**Files a user edited.** decman overwrites a managed file wholesale, so local edits are lost
rather than merged — but it also has no way to _transform_ one. Renaming a key inside a
config NosArch ships is fine (the whole file is replaced), while renaming a key inside a
config the user owns is not expressible at all.

**State outside the filesystem.** Flatpak remotes and installations, `yay`'s package
database, snapper metadata, anything a package's own hooks wrote. decman coordinates the
tools that own these; it does not model their contents.

## When migrations will be needed

A migration is for exactly the cases above: state that already exists on a user's machine
which convergence cannot reach. Moving a config file users have edited into a new location.
Removing something a NosArch version from before its declaration existed left behind.
Rewriting a value inside a user-owned file.

None of these exist yet, because NosArch has no users on older versions. **Do not build the
mechanism before the first real case.** The shape of that first migration will say more about
what is needed than any amount of design in advance, and a framework built against imagined
requirements will fit the real one badly.

When it arrives it should be a **separate mechanism**, not an extension of `on_change`. The
two have opposite requirements:

|                        | Migration  | `on_change`                   |
| ---------------------- | ---------- | ----------------------------- |
| Runs                   | Once, ever | Every time the module changes |
| Order                  | Guaranteed | Not guaranteed across modules |
| May assume prior state | Yes        | No                            |
| Must be idempotent     | No         | **Yes**                       |

A migration may do one-way transforms precisely because it is guaranteed not to re-run. An
`on_change` hook that assumes the same will corrupt what it touches on the next unrelated
change to its module. Keeping them separate keeps that distinction enforceable rather than a
matter of remembering.

What a migration system needs that `on_change` has none of: a version ledger recording which
migrations a machine has applied, a guaranteed order, and a defined answer for a machine that
skipped several versions at once.

## Interruption

Convergence is safe to interrupt. A run that dies halfway leaves the machine in a partial
state, and the next run re-derives whatever is still missing. Nothing needs to be unwound.

**Hooks are the exception, and they fail silently.** If a run is interrupted after files are
written but before or during `on_change`, the files are converged. On the next run nothing
has changed, so `module._changed` is false, so the hook never runs. The reload is lost, and
every subsequent run reports success.

Consequences scale with the command:

- A missed `sysctl --system` or `daemon-reload` means the old behaviour persists silently,
  exactly as if the hook had never been written.
- A missed or half-finished `limine-mkinitcpio` is the serious one: a truncated initramfs is
  an unbootable kernel entry.

**Recovery.** Run the command by hand; every command in `files.md`'s table is safe to run
directly. If the initramfs is the casualty, boot the other Limine entry and run
`limine-mkinitcpio` from there — this is the strongest practical argument for keeping the LTS
kernel enabled. To force a hook to re-run without knowing which one was lost, change a byte
in any file its module declares.

This is the one place where recording hook completion in decman's `Store` would earn its
complexity. It has not been built, because it has not yet bitten.

## Notes for changes that affect existing machines

- **Renaming or moving a NosArch-owned file is free.** Update the declaration; decman writes
  the new path and removes the old one. Check `tools/check_paths.py` passes, since references
  to the old path elsewhere in `dotfiles/` will not have moved with it.
- **Dropping a package is free.** Remove it from the module's package set.
- **Changing a file users are expected to edit is not free.** There is no merge. Prefer
  shipping defaults in a location users do not edit, with their overrides in a separate file.
- **A fresh install runs every hook at once.** New modules get `on_enable`, and `on_change`
  fires too since every file counts as changed. Hooks should be cheap enough that all of them
  running together is acceptable, because on a first install they will.
