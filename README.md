# refig

refig is a Python library for minimally-invasive reproducibility in Jupyter notebooks, with a focus on figures and plots.

## Installation

You can install refig using pip:

```bash
pip install refig
uv add refig
```

## Usage

To use refig, simply import it in your Jupyter notebook:

```python
from refig import refig
```

Then use `refig.savefig(NAME)` instead of `matplotlib.pyplot.savefig(PATH)` to save your figures with embedded metadata. `NAME` can end in `.png` or `.svg`.

When you save a figure, refig will automatically save the figure along with a steganographic pointer to the code that generated it, including (all optionally),

-   The notebook / file that generated the figure
-   The cell number (if applicable / available)
-   The date and time the figure was generated
-   The git commit hash (if applicable / available)

You can view these metadata by loading the figure with refig:

```python
uv run refig meta figure.png
uv run refig meta figure.svg
```

### Figure Saving Paths

By default, refig saves figures in a `figures/` directory. There are several subdirectories:

-   `figures/latest/`: Contains the most recently generated version of each figure.
-   `figures/history/`: Contains all historical versions of generated figures, sorted by timestamp and git commit hash.

For example,

```
figures/
    latest/
        figure1.png
        figure2.png
    history/
        figure1/
            _20250101_abcdef.png
            _20250201_bcdefa.png
        figure2/
            _20250115_cdefab.png
```
