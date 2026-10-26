# bluenixx_maintainers

The list of official Bluenixx maintainers, plus the place to apply. The build system reads `bluenixx.maintainers` from this repo to decide whether a build is OFFICIAL or UNOFFICIAL.

In the source tree this repo lives at `vendor/bluenixx_maintainers`, and the check in the build looks like this:

```make
ifeq ($(filter $(BLUENIXX_MAINTAINER):$(TARGET_PRODUCT),$(shell cat vendor/bluenixx_maintainers/bluenixx.maintainers 2>/dev/null)),)
```

So a build is only OFFICIAL when `BLUENIXX_MAINTAINER:TARGET_PRODUCT` is a line in that file.

## Before you apply

You need a device that already builds on Bluenixx, with its trees public:

- device tree
- vendor tree
- kernel tree

The device tree can be on GitHub or GitLab. The fork of this repo has to be on GitHub.

## Setting up your entry

Your name has to be written the same way in two places. A typo in either one and your builds stay UNOFFICIAL.

**1. Fork this repo**

Fork [Bluenixx/bluenixx_maintainers](https://github.com/Bluenixx/bluenixx_maintainers) and work on the branch you want reviewed.

**2. Add your line to `bluenixx.maintainers`**

One line per device, as `Name:bluenixx_codename`:

```
Zediss:bluenixx_bangkk
```

No spaces around the colon, and the codename is the one you use in `lunch`. Don't add comments to this file, make reads it word by word.

**3. Set the flag in your device tree**

In the root of your device tree, open `bluenixx_<codename>.mk` and add the same name:

```make
BLUENIXX_MAINTAINER := Zediss
```

For the example above that is `bluenixx_bangkk.mk`. Check that `PRODUCT_NAME` in the same file is `bluenixx_<codename>`, since that is the other half of the match.

## Applying

1. Open the [Issues tab](../../issues/new/choose) and pick **Maintainer application**.
2. Fill in your name, the codename and the links. If your changes are not on the default branch, add `/tree/<branch>` to the link.
3. Submit.

A bot answers in about a minute. It checks that:

- the name and codename are valid
- the device, vendor and kernel trees are reachable
- `bluenixx_<codename>.mk` exists and `BLUENIXX_MAINTAINER` matches your name
- your fork really is a fork of this repo
- your fork's `bluenixx.maintainers` has the line `Name:bluenixx_codename`
- nobody else is already listed for that device

If something fails you get `needs-changes` and a list of what to fix. Push the fix, then edit the issue or comment `/recheck`. When everything passes it becomes `ready-for-review`.

## After that

Passing the bot only means the setup is right. A reviewer then looks at the trees: does it build, does the device boot, are the basics working, is the history clean. They will comment on the issue if something needs changing.

When it is decided the issue closes as `approved` or `rejected`. If approved, open a pull request from your fork to this repo with your line in `bluenixx.maintainers`. Once it is merged, your builds can be marked OFFICIAL.

- One issue per device. If you maintain two, apply twice.
- Send the application when the fork is ready, the checks run as soon as you submit.
- Applying for a device that already has a maintainer is fine, but expect a conversation.

## Website

`site/` is a static page that lists every device in `bluenixx.maintainers` with a photo from the LineageOS wiki, the maintainers, whether it is active, and which build types (GApps, Vanilla) exist. There is no build step.

`scripts/build_data.py` writes `site/data/devices.json` from `bluenixx.maintainers`, the LineageOS wiki data and the OTA repo. The *Update site data* workflow runs it every 6 hours, on every change to `bluenixx.maintainers`, or by hand from the Actions tab, and commits the result. A device is active if it had a build in the last 60 days.

To host it on Cloudflare Pages: Workers & Pages > Create > Pages > Connect to Git, pick this repo, framework none, empty build command, output directory `site`.

## For the team

Add this repo to `bluenixx-manifest` so it syncs to `vendor/bluenixx_maintainers`.
