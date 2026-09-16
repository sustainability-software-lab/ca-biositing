# Notebook Setup Guide for **ca-biositing**

**Purpose** -- Set up Jupyter notebooks with correct imports for the PEP 420
namespace packages used in this repository.

---

## Prerequisites

| Requirement                                                | Command                                        | Note                                      |
| ---------------------------------------------------------- | ---------------------------------------------- | ----------------------------------------- |
| **Pixi** (v0.55+)                                          | `pixi --version`                               | Must be on `$PATH`.                       |
| **Project dependencies**                                   | `pixi install`                                 | Run from the repository root.             |
| **VS Code** with the **Python** and **Jupyter** extensions | Install via the Marketplace                    | Optional but recommended.                 |
| **Pixi Code** VS Code extension                            | Install from the recommended extensions prompt | Helps VS Code discover Pixi environments. |

---

## How it works

This project uses [pixi-kernel](https://github.com/renan-r-santos/pixi-kernel)
to provide a Jupyter kernel that runs code inside the Pixi environment. All
three namespace packages (`ca-biositing-datamodels`, `ca-biositing-pipeline`,
`ca-biositing-webservice`) are installed as editable PyPI packages via
`pixi.toml`, so they are importable without any `PYTHONPATH` configuration.

---

## Setup

1. Install the Pixi environment:

   ```bash
   pixi install
   ```

2. Register a stable Jupyter kernel for this workspace:

   ```bash
   pixi run register-jupyter-kernel
   ```

   This creates a kernel named **ca-biositing (Pixi)** that launches the Python
   executable from the active Pixi environment directly. It avoids relying on a
   global `python` command or VS Code's Pixi discovery cache.

3. Open a notebook in VS Code or launch JupyterLab:

   ```bash
   pixi run jupyter-lab
   ```

4. Select the **ca-biositing (Pixi)** or **Pixi** kernel for your notebook. In
   VS Code, click the kernel picker in the notebook toolbar, choose **Select
   Another Kernel**, then look under **Jupyter Kernels** first.

5. Imports work directly:

   ```python
   from ca_biositing.pipeline.utils.lookup_utils import replace_name_with_id_df
   from ca_biositing.datamodels.models import Resource
   ```

---

## Why this works

The repository is split into three independent distributions that share the
top-level namespace `ca_biositing`:

- `src/ca_biositing/datamodels`
- `src/ca_biositing/pipeline`
- `src/ca_biositing/webservice`

Each distribution is installed into the Pixi environment as an editable PyPI
package (see the `[feature.*.pypi-dependencies]` sections in `pixi.toml`).
Because `pixi-kernel` runs notebook code inside the Pixi environment, Python's
import machinery can find all three namespace sub-packages without any path
manipulation.

---

## VS Code IntelliSense

The `.vscode/settings.json` file includes `python.analysis.extraPaths` so that
the Python language server can resolve imports across the namespace packages for
code completion and linting. These are IDE-only settings and do not affect
runtime behavior.

On Windows, this repository uses Pixi's workspace Python at:

```text
.pixi\envs\default\python.exe
```

You do not need a separate system Python install for notebooks in this project.
If the plain `python` command opens the Microsoft Store or fails, that is okay
as long as `pixi run python --version` works.

---

## Verify the import works

Create a test cell in a notebook:

```python
import sys
print("Python executable:", sys.executable)

from ca_biositing.pipeline.utils.lookup_utils import replace_name_with_id_df
print("Import succeeded")
```

Expected output:

```
Python executable: /Users/.../.pixi/envs/default/bin/python
Import succeeded
```

---

## Summary

| Step                | Command / Action                                        |
| ------------------- | ------------------------------------------------------- |
| Install environment | `pixi install`                                          |
| Register kernel     | `pixi run register-jupyter-kernel`                      |
| Select kernel       | Choose **ca-biositing (Pixi)** in VS Code or JupyterLab |
| Import packages     | Use standard imports (`from ca_biositing.pipeline...`)  |

## Troubleshooting VS Code Kernel Discovery

Recent VS Code versions separate notebook kernel options into **Jupyter
Kernels**, **Python Environments**, and **Existing Jupyter Server**. If VS Code
asks for a URL, you are in **Existing Jupyter Server**; paste only an
`http://localhost:...` Jupyter URL there, not a Python executable path.

If **ca-biositing (Pixi)** does not appear after registering the kernel:

1. Run `Developer: Reload Window` in VS Code.
2. Open the kernel picker and choose **Select Another Kernel**.
3. Check **Jupyter Kernels** for **ca-biositing (Pixi)**.
4. If kernel discovery is still stale, start JupyterLab from Pixi:

   ```bash
   pixi run jupyter-lab
   ```

   Copy the printed `http://localhost:...token=...` URL into VS Code's
   **Existing Jupyter Server** URL box.
