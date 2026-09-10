# Adding Additional NEMO Versions / Branches

When setting up a project from this Cookiecutter template, initial NEMO versions are downloaded based on your input to `nemo_version` (e.g. `5.0.2`, `4.2.3`). 

If you want to add an additional NEMO version or feature branch to an existing project later, two options are available:

---

## Option 1: Using the `add_nemo_version.py` Script (Recommended)

This repository includes a standalone helper script in `scripts/add_nemo_version.py`. It downloads the specified version's namelists into `EXPREF/<version>/` and all reference files into `SHARED/<version>/` using the repository's configured components (`OCE`, `ICE`, `TOP`).

### Usage:
Run the following command from the root of your project directory:

```bash
python scripts/add_nemo_version.py <nemo_version_or_branch>
```

### Examples:
- **Adding a release version:**
  ```bash
  python scripts/add_nemo_version.py 5.0.2
  ```

- **Adding a feature branch:**
  ```bash
  python scripts/add_nemo_version.py 800-implement-single-last-barotropic-mode
  ```

### Why Option 1 is recommended:
- **Safe & Targeted:** Only creates `EXPREF/<new_ver>/` and `SHARED/<new_ver>/`.
- **No Git Merge Conflicts:** Never overwrites modified files in `MY_SRC/`, `CPP/`, or existing `EXPREF/` directories.

---

## Option 2: Updating `.cruft.json` and Running `cruft update`

If you are managing your project using [Cruft](https://github.com/cruft/cruft), you can update the template context stored in `.cruft.json`:

1. Open `.cruft.json` in the root of your generated repository.
2. Update `"nemo_version"` to include your new version or branch name, for example:
   ```json
   "nemo_version": "5.0.2, 800-implement-single-last-barotropic-mode"
   ```
3. Run `cruft update` from your terminal.

### Note on Option 2:
- `cruft update` will re-render the Cookiecutter template with the new context and execute the post-generation hook.
- **Important:** `cruft update` also attempts to pull upstream template updates and merge changes. If you have modified local project files, it may trigger git merge conflicts across your repository. Option 1 is usually safer for simply adding a new version.
