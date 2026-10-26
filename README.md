# Bluenixx maintainer applications

This is where you apply to maintain a device on Bluenixx. You open an issue with links to your trees, a bot checks that the basics are in place, and someone from the team reviews it after that.

## Before you apply

You need a device that already builds on Bluenixx, with its trees public:

- device tree
- vendor tree
- kernel tree
- a fork of [Bluenixx/vendor_lineage](https://github.com/Bluenixx/vendor_lineage) with your entry in it (steps below)

The device tree can live on GitHub or GitLab. The `vendor_lineage` fork has to be on GitHub.

## Setting up your entry

Your maintainer name has to be written the same way in two places. We use it to mark builds as OFFICIAL, so a typo here means your builds stay UNOFFICIAL.

**1. Fork `vendor_lineage`**

Fork [Bluenixx/vendor_lineage](https://github.com/Bluenixx/vendor_lineage) to your own account and work on the branch you want to be reviewed.

**2. Add yourself to `bluenixx.maintainers`**

The file is in the root of the repo. Add one line per device, as `Name:bluenixx_codename`:

```
Zediss:bluenixx_bangkk
```

No spaces around the colon. The codename is the same one used in `lunch`.

**3. Set the flag in your device tree**

Open `bluenixx_<codename>.mk` in the root of your device tree and add the flag with the exact same name:

```make
BLUENIXX_MAINTAINER := Zediss
```

For the example above the file would be `bluenixx_bangkk.mk`. While you are in there, check that `PRODUCT_NAME` is `bluenixx_<codename>`, the check compares them.

## Applying

1. Go to the [Issues tab](../../issues/new/choose) and pick **Maintainer application**.
2. Fill in your name, the codename and the links. If your changes are not on the default branch, paste the link with `/tree/<branch>` at the end.
3. Submit it.

The bot replies within a minute or so. It checks that:

- the name and codename are written in a valid way
- the device tree, vendor tree and kernel tree are reachable
- `bluenixx_<codename>.mk` exists in the device tree and `BLUENIXX_MAINTAINER` matches the name you gave
- your fork really is a fork of `Bluenixx/vendor_lineage`
- `bluenixx.maintainers` in your fork has the line `Name:bluenixx_codename`
- nobody else is already listed for that device

If something fails you get the `needs-changes` label and a list of what to fix. Push the fix, then edit the issue or comment `/recheck` and the checks run again. When everything passes the issue gets `ready-for-review`.

## What happens next

Passing the bot only means the setup is correct. A reviewer then looks at the trees themselves: whether it builds, whether the device boots and the basics work, and whether the history is clean. They will comment on the issue if they need something changed.

When the decision is made the issue is closed with an `approved` or `rejected` label. If it is approved, the team will contact you to finish the process.

## Notes

- One issue per device. If you maintain two, apply twice.
- Don't send your application before the fork is ready. The checks run as soon as you submit.
- Applying for a device that already has a maintainer is fine, but expect a conversation about it.
- Questions that are not about an application should go to the team directly, not here.
