# QuantLib-vega

An extension of the QuantLib-SWIG Python bindings, optimized and distributed under the name **QuantLib-vega**.

This project is a fork of the official [QuantLib-SWIG](https://github.com) repository. It provides Python wrappers for the QuantLib quantitative finance library.

## Installation

Install the package via pip:

```bash
pip install QuantLib-vega
```

## Usage

You can import and use this package exactly like the original `QuantLib` library:

```python
import QuantLib as ql

# Example: Create a date
date = ql.Date(7, 7, 2026)
print(f"Date: {date}")
```

## About the Fork

**QuantLib-vega** is maintained independently from the core QuantLib development team. While it retains full compatibility with the original SWIG bindings, this distribution may include specific patches, configurations, or optimizations tailored for vega-specific workflows.

## License

This project is licensed under the **QuantLib License**. 

QuantLib is Open Source and its license is a slightly modified version of the BSD License. You can use, modify, and distribute this software for both commercial and non-commercial purposes.
