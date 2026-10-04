# Known-good release bundle

This folder collects the previously working GUI baseline and its runtime prompt and brand assets. It intentionally excludes the later `플러그인진단3` diagnostic build and local marketplace/account configuration.

## Contents

- `상세페이지 자동화 GUI.exe`: desktop file `상세페이지 자동화 GUI - 플러그인연결.exe`, copied without modification. SHA-256: `f88569e1ce7a5e65253a3ca22a2b6504e52bea126179919ae501f5b70520170a`.
- `brand_logo.png`: brand logo asset used by the GUI.
- `prompt_overrides/`: per-section and thumbnail prompt files, including empty templates and their README. Empty files are intentional defaults, not missing files.
- `examples/product-specific-additional-prompt.txt`: the saved 1,799-character extra prompt, separated from the local GUI configuration. It is an example for one product and is not a universal default.

The repository root also contains the recovered Python source, requirements, upgrade scripts, and tests. The EXE is stored through Git LFS. On another PC, install Git LFS before cloning or use Git LFS checkout so the EXE downloads as a real binary rather than a pointer file. ChatGPT login and browser availability remain local to that PC.

No `detail_page_gui_config.json`, credentials, marketplace secrets, browser profile, product URL history, or diagnostic candidate is included.
