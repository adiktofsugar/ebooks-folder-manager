# Getting your Adobe Digital Editions key

> **You only need to do this by hand on Linux.** On Windows and macOS, install and authorize ADE (steps 1–2 below), then run `uv run efm setup adobe-key`, which runs the same script for you.

Books bought through Adobe (anything delivered as an `.acsm` file) are encrypted with a key tied to your Adobe ID. To decrypt them you need that key as a `.der` file.

[DeDRM_tools](https://github.com/noDRM/DeDRM_tools) (the `DeDRM_tools/` submodule) has a script, `DeDRM_plugin/adobekey.py`, that reads the key out of an authorized install of [Adobe Digital Editions](https://www.adobe.com/solutions/ebook/digital-editions/download.html) (ADE). On Windows it reads the registry, and on macOS it reads ADE's `activation.dat`.

## Manual steps (Windows / macOS)

1. Install ADE from the [download page](https://www.adobe.com/solutions/ebook/digital-editions/download.html).

2. Open ADE and authorize it with your Adobe ID: Help → Authorize Computer. The key is created at this point, so it has to be the same Adobe ID you buy books with.

3. Run the script. It uses relative imports, so run it as a module from `DeDRM_tools/` rather than as `python adobekey.py`. efm's uv environment already has the dependency it needs (`pycryptodomex`). Pass an output directory (with no arguments it opens a Tk GUI instead):

   ```bash
   cd DeDRM_tools
   mkdir -p ~/adobe-keys
   uv run python -m DeDRM_plugin.adobekey ~/adobe-keys
   ```

   You should see `Saved a key to .../adobekey1_uuid_<uuid>.der`, one file per key found.

4. Tell efm where the key is, either through `uv run efm setup save-config` or directly in your config file:

   ```toml
   # efm.toml
   adobekey = "/home/you/adobe-keys/adobekey1_uuid_....der"
   ```

   It's just a path, so keep the `.der` file somewhere it won't get deleted.

## Linux

ADE only runs on Windows and macOS, so on Linux you run both ADE and the script under [Wine](https://www.winehq.org/), using the Windows code path. That means a second, Windows Python inside Wine, separate from the one uv manages, which is...weird. Here's how the steps above change:

1. Install Wine (e.g. `sudo dnf install wine` or `sudo apt install wine`).

2. Install ADE under Wine. Get the Windows installer from the "Manually install Adobe Digital Editions for Windows" section of the [download page](https://www.adobe.com/solutions/ebook/digital-editions/download.html), then:

   ```bash
   wine ADE_4.5_Installer.exe
   ```

3. Authorize ADE as above. Open it with:

   ```bash
   wine "$HOME/.wine/drive_c/Program Files (x86)/Adobe/Adobe Digital Editions 4.5/DigitalEditions.exe"
   ```

4. Install Windows Python under Wine, using the "Windows installer (64-bit)" from [python.org](https://www.python.org/downloads/windows/), and the one dependency the script needs:

   ```bash
   wine python-3.x.y-amd64.exe     # check "Add python.exe to PATH"
   wine python --version
   wine python -m pip install pycryptodome
   ```

5. Run the script with Wine's Python instead of uv's:

   ```bash
   cd DeDRM_tools
   mkdir -p ~/adobe-keys
   wine python -m DeDRM_plugin.adobekey ~/adobe-keys
   ```

   Wine maps `/` to `Z:\`, so Linux paths work.

6. Save the key path to the config as in step 4 above.

## Making this less manual

`efm setup adobe-key` only runs the script with uv's Python, so it can't handle Linux. Eventually efm should do the Linux case itself: detect ADE in the Wine prefix, set up the Wine Python and `pycryptodome` if they're missing, run `adobekey` under Wine, and save the resulting path to the config, so all you have to do is install and authorize ADE.
