# Changelog

## [Unreleased]

- Initial release split from [`netsquid-qp4/europ4-2020`](https://gitlab.com/softwarequtech/netsquid-snippets/netsquid-qp4/-/tree/europ4-2020),
  but:
  - It only contains non-simulator specific code.
  - It only contains implementations for architectures supported by the mainline P4C (currently,
    only V1Model).
- Feature-wise, largely the same as the original code `netsquid-qp4/europ4-2020` code except for:
  - Generally refactored for better extensibility.
  - Convenience features added (such as logging).
  - There are now separate program and process abstractions.

